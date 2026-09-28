"""Service for partner referral management, commission calculations, and statements."""

from __future__ import annotations

import secrets
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.core.ids import uuid7
from app.modules.partner.models import CommissionEntry, CommissionRule, Partner
from app.modules.partner.repository import PartnerRepository
from app.modules.partner.schemas import (
    CommissionRuleCreate,
    PartnerCreate,
    PartnerStatementOut,
)


class PartnerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PartnerRepository(session)

    async def _next_code(self) -> str:
        token = secrets.randbelow(900) + 100
        return f"PRT-{token}"

    async def create_partner(self, data: PartnerCreate) -> Partner:
        code = await self._next_code()
        partner = Partner(
            id=uuid7(),
            partner_type=data.partner_type,
            name=data.name,
            code=code,
            phone=data.phone,
            email=data.email,
            centre_id=data.centre_id,
            commission_payout_type=data.commission_payout_type,
            status="ACTIVE",
        )
        self.session.add(partner)
        await self.session.commit()
        return await self.repo.get_by_id(partner.id)  # type: ignore[return-value]

    async def add_rule(self, data: CommissionRuleCreate) -> CommissionRule:
        partner = await self.repo.get_by_id(data.partner_id)
        if not partner:
            raise NotFound(message="Partner not found")

        rule = CommissionRule(
            id=uuid7(),
            partner_id=data.partner_id,
            scope=data.scope,
            target_id=data.target_id,
            rule_type=data.rule_type,
            value=data.value,
            effective_from=data.effective_from,
            is_active=True,
        )
        self.session.add(rule)
        await self.session.commit()
        return rule

    async def record_commission_for_booking(
        self, partner_id: uuid.UUID, booking_id: uuid.UUID, gross_amount: int
    ) -> CommissionEntry:
        partner = await self.repo.get_by_id(partner_id)
        if not partner:
            raise NotFound(message="Partner not found")

        rules = await self.repo.list_rules(partner_id)
        rate = 10.0  # default 10%
        if rules:
            rate = float(rules[0].value)

        commission_amount = int(gross_amount * (rate / 100.0))
        net_amount = gross_amount - commission_amount

        entry = CommissionEntry(
            id=uuid7(),
            partner_id=partner_id,
            booking_id=booking_id,
            gross_amount=gross_amount,
            commission_amount=commission_amount,
            net_amount=net_amount,
            status="APPROVED",
        )
        self.session.add(entry)
        await self.session.commit()
        return entry

    async def generate_statement(
        self, partner_id: uuid.UUID, period: str = "current"
    ) -> PartnerStatementOut:
        partner = await self.repo.get_by_id(partner_id)
        if not partner:
            raise NotFound(message="Partner not found")

        entries = await self.repo.list_entries(partner_id)
        total_referrals = len(entries)
        gross_revenue = sum(e.gross_amount for e in entries)
        earned_commission = sum(e.commission_amount for e in entries)
        platform_net = sum(e.net_amount for e in entries)
        pending_commission = sum(e.commission_amount for e in entries if e.status != "PAID")
        paid_commission = sum(e.commission_amount for e in entries if e.status == "PAID")

        return PartnerStatementOut(
            partner_id=partner.id,
            partner_name=partner.name,
            partner_code=partner.code,
            period=period,
            total_referrals=total_referrals,
            gross_revenue=gross_revenue,
            earned_commission=earned_commission,
            platform_net=platform_net,
            pending_commission=pending_commission,
            paid_commission=paid_commission,
            entries=list(entries),
        )
