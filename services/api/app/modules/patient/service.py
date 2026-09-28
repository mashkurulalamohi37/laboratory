"""Business service for patient management."""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.modules.patient.models import Address, FamilyLink, Patient
from app.modules.patient.repository import PatientRepository
from app.modules.patient.schemas import (
    AddressCreate,
    AddressUpdate,
    FamilyMemberCreate,
    PatientUpdate,
)


class PatientService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PatientRepository(session)

    async def get_or_create_for_user(
        self,
        *,
        user_id: uuid.UUID,
        full_name: str | None = None,
        phone: str | None = None,
    ) -> Patient:
        patient = await self.repo.get_by_owner(user_id)
        if patient:
            return patient

        # Create self profile
        name = full_name or "Account Holder"
        patient = await self.repo.create_patient(
            full_name=name,
            dob=dt.date(1990, 1, 1),
            sex="M",
            phone=phone,
            owner_user_id=user_id,
        )
        await self.repo.link_family(user_id=user_id, patient_id=patient.id, relationship="SELF")
        return patient

    async def get_family_members(self, user_id: uuid.UUID) -> Sequence[FamilyLink]:
        # Ensure self patient exists
        await self.get_or_create_for_user(user_id=user_id)
        return await self.repo.get_family_members(user_id)

    async def add_family_member(
        self,
        user_id: uuid.UUID,
        data: FamilyMemberCreate,
    ) -> FamilyLink:
        patient = await self.repo.create_patient(
            full_name=data.full_name,
            full_name_bn=data.full_name_bn,
            dob=data.dob,
            sex=data.sex,
            phone=data.phone,
            blood_group=data.blood_group,
            owner_user_id=None,
        )
        link = await self.repo.link_family(
            user_id=user_id,
            patient_id=patient.id,
            relationship=data.relationship,
        )
        # Reload with patient relation
        family = await self.repo.get_family_members(user_id)
        for item in family:
            if item.id == link.id:
                return item
        return link

    async def remove_family_member(self, user_id: uuid.UUID, patient_id: uuid.UUID) -> None:
        removed = await self.repo.remove_family_link(user_id, patient_id)
        if not removed:
            raise NotFound("Family member not found")

    async def update_patient(
        self,
        patient_id: uuid.UUID,
        data: PatientUpdate,
    ) -> Patient:
        patient = await self.repo.get_by_id(patient_id)
        if not patient:
            raise NotFound("Patient not found")
        if data.full_name is not None:
            patient.full_name = data.full_name
        if data.full_name_bn is not None:
            patient.full_name_bn = data.full_name_bn
        if data.dob is not None:
            patient.dob = data.dob
        if data.sex is not None:
            patient.sex = data.sex
        if data.phone is not None:
            patient.phone = data.phone
        if data.blood_group is not None:
            patient.blood_group = data.blood_group
        await self.session.flush()
        return patient

    async def list_addresses(self, user_id: uuid.UUID) -> Sequence[Address]:
        return await self.repo.get_addresses(user_id)

    async def create_address(self, user_id: uuid.UUID, data: AddressCreate) -> Address:
        return await self.repo.create_address(
            user_id=user_id,
            patient_id=data.patient_id,
            division_id=data.division_id,
            district_id=data.district_id,
            upazila_id=data.upazila_id,
            area_id=data.area_id,
            house=data.house,
            road=data.road,
            block=data.block,
            landmark=data.landmark,
            label=data.label,
            is_default=data.is_default,
        )

    async def update_address(
        self, user_id: uuid.UUID, address_id: uuid.UUID, data: AddressUpdate
    ) -> Address:
        addr = await self.repo.get_address(address_id, user_id)
        if not addr:
            raise NotFound("Address not found")
        if data.division_id is not None:
            addr.division_id = data.division_id
        if data.district_id is not None:
            addr.district_id = data.district_id
        if data.upazila_id is not None:
            addr.upazila_id = data.upazila_id
        if data.area_id is not None:
            addr.area_id = data.area_id
        if data.house is not None:
            addr.house = data.house
        if data.road is not None:
            addr.road = data.road
        if data.block is not None:
            addr.block = data.block
        if data.landmark is not None:
            addr.landmark = data.landmark
        if data.label is not None:
            addr.label = data.label
        if data.is_default is not None:
            addr.is_default = data.is_default
        await self.session.flush()
        return addr

    async def delete_address(self, user_id: uuid.UUID, address_id: uuid.UUID) -> None:
        deleted = await self.repo.delete_address(address_id, user_id)
        if not deleted:
            raise NotFound("Address not found")
