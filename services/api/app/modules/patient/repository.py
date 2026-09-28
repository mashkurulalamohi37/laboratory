"""Database repository for patient module."""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.modules.patient.models import Address, FamilyLink, Patient


class PatientRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def next_patient_code(self) -> str:
        year = dt.datetime.now(dt.UTC).year
        prefix = f"PT-{year}-"
        query = select(func.count(Patient.id)).where(Patient.patient_code.like(f"{prefix}%"))
        count = (await self.session.execute(query)).scalar_one()
        return f"{prefix}{count + 1:06d}"

    async def get_by_id(self, patient_id: uuid.UUID) -> Patient | None:
        query = select(Patient).where(Patient.id == patient_id)
        return (await self.session.execute(query)).scalar_one_or_none()

    async def get_by_owner(self, owner_user_id: uuid.UUID) -> Patient | None:
        query = select(Patient).where(Patient.owner_user_id == owner_user_id)
        return (await self.session.execute(query)).scalar_one_or_none()

    async def create_patient(
        self,
        *,
        full_name: str,
        dob: dt.date,
        sex: str,
        full_name_bn: str | None = None,
        phone: str | None = None,
        blood_group: str | None = None,
        owner_user_id: uuid.UUID | None = None,
    ) -> Patient:
        code = await self.next_patient_code()
        patient = Patient(
            patient_code=code,
            full_name=full_name,
            full_name_bn=full_name_bn,
            dob=dob,
            sex=sex,
            phone=phone,
            blood_group=blood_group,
            owner_user_id=owner_user_id,
        )
        self.session.add(patient)
        await self.session.flush()
        return patient

    async def link_family(
        self,
        *,
        user_id: uuid.UUID,
        patient_id: uuid.UUID,
        relationship: str = "OTHER",
    ) -> FamilyLink:
        link = FamilyLink(user_id=user_id, patient_id=patient_id, relationship=relationship)
        self.session.add(link)
        await self.session.flush()
        return link

    async def get_family_members(self, user_id: uuid.UUID) -> Sequence[FamilyLink]:
        query = (
            select(FamilyLink)
            .where(FamilyLink.user_id == user_id)
            .options(joinedload(FamilyLink.patient))
            .order_by(FamilyLink.created_at.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def remove_family_link(self, user_id: uuid.UUID, patient_id: uuid.UUID) -> bool:
        link = (
            await self.session.execute(
                select(FamilyLink).where(
                    FamilyLink.user_id == user_id,
                    FamilyLink.patient_id == patient_id,
                )
            )
        ).scalar_one_or_none()
        if not link:
            return False
        await self.session.delete(link)
        await self.session.flush()
        return True

    async def get_addresses(self, user_id: uuid.UUID) -> Sequence[Address]:
        query = (
            select(Address)
            .where(Address.user_id == user_id)
            .order_by(Address.is_default.desc(), Address.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_address(self, address_id: uuid.UUID, user_id: uuid.UUID) -> Address | None:
        query = select(Address).where(Address.id == address_id, Address.user_id == user_id)
        return (await self.session.execute(query)).scalar_one_or_none()

    async def create_address(
        self,
        *,
        user_id: uuid.UUID,
        patient_id: uuid.UUID | None = None,
        division_id: uuid.UUID | None = None,
        district_id: uuid.UUID | None = None,
        upazila_id: uuid.UUID | None = None,
        area_id: uuid.UUID | None = None,
        house: str,
        road: str | None = None,
        block: str | None = None,
        landmark: str | None = None,
        label: str = "HOME",
        is_default: bool = False,
    ) -> Address:
        if is_default:
            # Unset existing default
            await self.session.execute(
                update(Address).where(Address.user_id == user_id).values(is_default=False)
            )
        addr = Address(
            user_id=user_id,
            patient_id=patient_id,
            division_id=division_id,
            district_id=district_id,
            upazila_id=upazila_id,
            area_id=area_id,
            house=house,
            road=road,
            block=block,
            landmark=landmark,
            label=label,
            is_default=is_default,
        )
        self.session.add(addr)
        await self.session.flush()
        return addr

    async def delete_address(self, address_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        addr = await self.get_address(address_id, user_id)
        if not addr:
            return False
        await self.session.delete(addr)
        await self.session.flush()
        return True
