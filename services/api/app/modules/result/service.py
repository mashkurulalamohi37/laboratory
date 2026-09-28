"""Business logic for result entry, reference range matching, critical alerts and verification."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound, PermissionDenied
from app.modules.catalog.models import ReferenceRange, TestParameter
from app.modules.catalog.ranges import Flag, RangeRule, Subject, evaluate, select_range
from app.modules.lab.models import LabOrderItem, OrderItemStatus
from app.modules.result.models import (
    AlertStatus,
    CriticalAlert,
    Result,
    ResultComment,
    ResultFlag,
    ResultParameter,
    ResultStatus,
)
from app.modules.result.repository import ResultRepository
from app.modules.result.schemas import (
    AlertAcknowledgeRequest,
    ParameterEntry,
    ResultAmendRequest,
    ResultEnterRequest,
    ResultReturnRequest,
    ResultVerifyRequest,
)


class ResultService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ResultRepository(session)

    async def _fetch_parameter_rules(
        self, parameter_id: uuid.UUID
    ) -> tuple[TestParameter | None, list[RangeRule]]:
        stmt = select(TestParameter).where(TestParameter.id == parameter_id)
        res = await self._session.execute(stmt)
        param = res.scalar_one_or_none()
        if not param:
            return None, []

        range_stmt = select(ReferenceRange).where(ReferenceRange.parameter_id == parameter_id)
        range_res = await self._session.execute(range_stmt)
        ranges = range_res.scalars().all()

        rules = [
            RangeRule(
                id=r.id,
                sex=r.sex,
                age_min_days=r.age_min_days,
                age_max_days=r.age_max_days,
                sample_type_id=r.sample_type_id,
                lab_id=r.lab_id,
                method=r.method,
                effective_from=r.effective_from,
                effective_to=r.effective_to,
                low=r.low,
                high=r.high,
                critical_low=r.critical_low,
                critical_high=r.critical_high,
                text_normal=r.text_normal,
            )
            for r in ranges
        ]
        return param, rules

    def _evaluate_entry(
        self, p_entry: ParameterEntry, rules: list[RangeRule], subject: Subject
    ) -> tuple[str, bool, dict[str, Any] | None]:
        matched_rule = select_range(rules, subject)
        if not matched_rule:
            return ResultFlag.N, False, None

        ref_snapshot: dict[str, Any] = {
            "rule_id": str(matched_rule.id),
            "low": str(matched_rule.low) if matched_rule.low is not None else None,
            "high": str(matched_rule.high) if matched_rule.high is not None else None,
            "critical_low": (
                str(matched_rule.critical_low) if matched_rule.critical_low is not None else None
            ),
            "critical_high": (
                str(matched_rule.critical_high) if matched_rule.critical_high is not None else None
            ),
            "text_normal": matched_rule.text_normal,
        }

        if p_entry.value_numeric is None:
            return ResultFlag.N, False, ref_snapshot

        eval_flag = evaluate(Decimal(str(p_entry.value_numeric)), matched_rule)
        flag_map = {
            Flag.CRITICAL_LOW: (ResultFlag.CL, True),
            Flag.CRITICAL_HIGH: (ResultFlag.CH, True),
            Flag.LOW: (ResultFlag.L, False),
            Flag.HIGH: (ResultFlag.H, False),
            Flag.NORMAL: (ResultFlag.N, False),
        }
        flag_str, is_crit = flag_map.get(eval_flag, (ResultFlag.N, False))
        return flag_str, is_crit, ref_snapshot

    async def enter_results(self, data: ResultEnterRequest, actor_id: uuid.UUID) -> Result:
        item_stmt = select(LabOrderItem).where(LabOrderItem.id == data.lab_order_item_id)
        item_res = await self._session.execute(item_stmt)
        item = item_res.scalar_one_or_none()
        if not item:
            raise NotFound(code="LAB_ITEM_NOT_FOUND", message="Lab order item not found")

        now = datetime.now(UTC)
        result_obj = await self._repo.get_current_result(data.lab_order_item_id)
        if not result_obj:
            result_obj = Result(
                lab_order_item_id=data.lab_order_item_id,
                status=ResultStatus.ENTERED,
                version=1,
                is_current=True,
                entered_by=actor_id,
                entered_at=now,
            )
            await self._repo.save_result(result_obj)
        else:
            result_obj.status = ResultStatus.ENTERED
            result_obj.entered_by = actor_id
            result_obj.entered_at = now
            result_obj.parameters.clear()
            result_obj.comments.clear()

        subject = Subject(
            sex=data.patient_sex,
            age_days=data.patient_dob_days or (30 * 365),
            on=now.date(),
        )

        for p_entry in data.parameters:
            param, rules = await self._fetch_parameter_rules(p_entry.parameter_id)
            if not param:
                continue

            flag_str, is_crit, ref_snapshot = self._evaluate_entry(p_entry, rules, subject)
            res_param = ResultParameter(
                result_id=result_obj.id,
                parameter_id=p_entry.parameter_id,
                value_numeric=p_entry.value_numeric,
                value_text=p_entry.value_text,
                value_option=p_entry.value_option,
                unit_snapshot=param.unit,
                ref_range_snapshot=ref_snapshot,
                flag=flag_str,
                is_critical=is_crit,
            )
            self._session.add(res_param)
            await self._session.flush()

            if is_crit:
                alert = CriticalAlert(
                    result_parameter_id=res_param.id,
                    lab_order_item_id=item.id,
                    alert_type="CRITICAL_HIGH" if flag_str == ResultFlag.CH else "CRITICAL_LOW",
                    message=f"Critical {param.name}: {p_entry.value_numeric} {param.unit or ''}",
                    status=AlertStatus.TRIGGERED,
                    notified_users=[{"role": "PATHOLOGIST"}, {"role": "LAB_MANAGER"}],
                )
                await self._repo.save_alert(alert)

        for comment_txt in data.comments:
            self._session.add(
                ResultComment(
                    result_id=result_obj.id,
                    author_id=actor_id,
                    comment_type="CLINICAL",
                    comment_text=comment_txt,
                    created_at=now,
                )
            )

        result_obj.status = ResultStatus.PENDING_VERIFICATION
        item.status = OrderItemStatus.RESULT_ENTERED
        self._session.add(item)
        await self._session.flush()

        return (await self._repo.get_result_by_id(result_obj.id)) or result_obj

    async def verify_result(
        self, result_id: uuid.UUID, data: ResultVerifyRequest, actor_id: uuid.UUID
    ) -> Result:
        result_obj = await self._repo.get_result_by_id(result_id)
        if not result_obj:
            raise NotFound(code="RESULT_NOT_FOUND", message="Result not found")

        if result_obj.entered_by and result_obj.entered_by == actor_id:
            raise PermissionDenied(
                code="FOUR_EYES_VIOLATION",
                message=(
                    "Pathologist verification requires a different user than the result enterer"
                ),
            )

        now = datetime.now(UTC)
        result_obj.status = ResultStatus.VERIFIED
        result_obj.verified_by = actor_id
        result_obj.verified_at = now

        if data.comments:
            self._session.add(
                ResultComment(
                    result_id=result_obj.id,
                    author_id=actor_id,
                    comment_type="CLINICAL",
                    comment_text=f"Verification note: {data.comments}",
                    created_at=now,
                )
            )

        item_stmt = select(LabOrderItem).where(LabOrderItem.id == result_obj.lab_order_item_id)
        item_res = await self._session.execute(item_stmt)
        item = item_res.scalar_one_or_none()
        if item:
            item.status = OrderItemStatus.VERIFIED
            self._session.add(item)

        await self._repo.save_result(result_obj)
        return result_obj

    async def return_result(
        self, result_id: uuid.UUID, data: ResultReturnRequest, actor_id: uuid.UUID
    ) -> Result:
        result_obj = await self._repo.get_result_by_id(result_id)
        if not result_obj:
            raise NotFound(code="RESULT_NOT_FOUND", message="Result not found")

        now = datetime.now(UTC)
        result_obj.status = ResultStatus.RETURNED

        comment = ResultComment(
            result_id=result_obj.id,
            author_id=actor_id,
            comment_type="INTERNAL",
            comment_text=f"Returned for correction: {data.reason}",
            created_at=now,
        )
        self._session.add(comment)
        await self._repo.save_result(result_obj)
        return result_obj

    async def amend_result(
        self, result_id: uuid.UUID, data: ResultAmendRequest, actor_id: uuid.UUID
    ) -> Result:
        old_result = await self._repo.get_result_by_id(result_id)
        if not old_result:
            raise NotFound(code="RESULT_NOT_FOUND", message="Result not found")

        now = datetime.now(UTC)
        old_result.is_current = False
        old_result.status = ResultStatus.AMENDED
        old_result.amended_by = actor_id
        old_result.amended_at = now
        old_result.amend_reason = data.reason
        await self._repo.save_result(old_result)

        new_result = Result(
            lab_order_item_id=old_result.lab_order_item_id,
            status=ResultStatus.PENDING_VERIFICATION,
            version=old_result.version + 1,
            is_current=True,
            entered_by=actor_id,
            entered_at=now,
            amend_reason=data.reason,
        )
        await self._repo.save_result(new_result)

        subject = Subject(sex=None, age_days=30 * 365, on=now.date())
        for p_entry in data.parameters:
            param, rules = await self._fetch_parameter_rules(p_entry.parameter_id)
            if not param:
                continue
            flag_str, is_crit, ref_snapshot = self._evaluate_entry(p_entry, rules, subject)
            res_param = ResultParameter(
                result_id=new_result.id,
                parameter_id=p_entry.parameter_id,
                value_numeric=p_entry.value_numeric,
                value_text=p_entry.value_text,
                value_option=p_entry.value_option,
                unit_snapshot=param.unit,
                ref_range_snapshot=ref_snapshot,
                flag=flag_str,
                is_critical=is_crit,
            )
            self._session.add(res_param)

        for comment_txt in data.comments:
            self._session.add(
                ResultComment(
                    result_id=new_result.id,
                    author_id=actor_id,
                    comment_type="CLINICAL",
                    comment_text=comment_txt,
                    created_at=now,
                )
            )

        await self._session.flush()
        return (await self._repo.get_result_by_id(new_result.id)) or new_result

    async def get_current_result(self, lab_order_item_id: uuid.UUID) -> Result | None:
        return await self._repo.get_current_result(lab_order_item_id)

    async def get_result_by_id(self, result_id: uuid.UUID) -> Result | None:
        return await self._repo.get_result_by_id(result_id)

    async def list_critical_alerts(self, status: str | None = None) -> Sequence[CriticalAlert]:
        return await self._repo.list_critical_alerts(status)

    async def acknowledge_alert(
        self, alert_id: uuid.UUID, data: AlertAcknowledgeRequest, actor_id: uuid.UUID
    ) -> CriticalAlert:
        alert = await self._repo.get_alert_by_id(alert_id)
        if not alert:
            raise NotFound(code="ALERT_NOT_FOUND", message="Critical alert not found")
        now = datetime.now(UTC)
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by = actor_id
        alert.acknowledged_at = now
        alert.action_taken = data.action_taken
        return await self._repo.save_alert(alert)
