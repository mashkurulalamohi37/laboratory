"""FastAPI router for patient profiles, family members, and addresses."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.responses import Envelope, ok
from app.modules.auth.dependencies import CurrentPrincipal
from app.modules.patient.schemas import (
    AddressCreate,
    AddressResponse,
    AddressUpdate,
    FamilyMemberCreate,
    FamilyMemberResponse,
    PatientResponse,
    PatientUpdate,
)
from app.modules.patient.service import PatientService

router = APIRouter(tags=["patient"])


def get_patient_service(session: Annotated[AsyncSession, Depends(get_session)]) -> PatientService:
    return PatientService(session)


@router.get("/patients/me", response_model=Envelope[PatientResponse])
async def get_my_patient_profile(
    principal: CurrentPrincipal,
    service: Annotated[PatientService, Depends(get_patient_service)],
) -> Envelope[PatientResponse]:
    patient = await service.get_or_create_for_user(user_id=principal.user_id)
    return ok(PatientResponse.model_validate(patient))


@router.patch("/patients/{patient_id}", response_model=Envelope[PatientResponse])
async def update_patient(
    patient_id: uuid.UUID,
    body: PatientUpdate,
    principal: CurrentPrincipal,
    service: Annotated[PatientService, Depends(get_patient_service)],
) -> Envelope[PatientResponse]:
    patient = await service.update_patient(patient_id, body)
    return ok(PatientResponse.model_validate(patient))


@router.get("/patients/family", response_model=Envelope[list[FamilyMemberResponse]])
async def get_family_members(
    principal: CurrentPrincipal,
    service: Annotated[PatientService, Depends(get_patient_service)],
) -> Envelope[list[FamilyMemberResponse]]:
    links = await service.get_family_members(principal.user_id)
    items = [
        FamilyMemberResponse(
            id=link.id,
            user_id=link.user_id,
            patient_id=link.patient_id,
            relationship=link.relationship,
            patient=PatientResponse.model_validate(link.patient),
        )
        for link in links
    ]
    return ok(items)


@router.post(
    "/patients/family",
    response_model=Envelope[FamilyMemberResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_family_member(
    body: FamilyMemberCreate,
    principal: CurrentPrincipal,
    service: Annotated[PatientService, Depends(get_patient_service)],
) -> Envelope[FamilyMemberResponse]:
    link = await service.add_family_member(principal.user_id, body)
    res = FamilyMemberResponse(
        id=link.id,
        user_id=link.user_id,
        patient_id=link.patient_id,
        relationship=link.relationship,
        patient=PatientResponse.model_validate(link.patient),
    )
    return ok(res)


@router.delete("/patients/family/{patient_id}", response_model=Envelope[dict[str, bool]])
async def delete_family_member(
    patient_id: uuid.UUID,
    principal: CurrentPrincipal,
    service: Annotated[PatientService, Depends(get_patient_service)],
) -> Envelope[dict[str, bool]]:
    await service.remove_family_member(principal.user_id, patient_id)
    return ok({"deleted": True})


@router.get("/addresses", response_model=Envelope[list[AddressResponse]])
async def list_addresses(
    principal: CurrentPrincipal,
    service: Annotated[PatientService, Depends(get_patient_service)],
) -> Envelope[list[AddressResponse]]:
    addrs = await service.list_addresses(principal.user_id)
    return ok([AddressResponse.model_validate(a) for a in addrs])


@router.post(
    "/addresses",
    response_model=Envelope[AddressResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_address(
    body: AddressCreate,
    principal: CurrentPrincipal,
    service: Annotated[PatientService, Depends(get_patient_service)],
) -> Envelope[AddressResponse]:
    addr = await service.create_address(principal.user_id, body)
    return ok(AddressResponse.model_validate(addr))


@router.patch("/addresses/{address_id}", response_model=Envelope[AddressResponse])
async def update_address(
    address_id: uuid.UUID,
    body: AddressUpdate,
    principal: CurrentPrincipal,
    service: Annotated[PatientService, Depends(get_patient_service)],
) -> Envelope[AddressResponse]:
    addr = await service.update_address(principal.user_id, address_id, body)
    return ok(AddressResponse.model_validate(addr))


@router.delete("/addresses/{address_id}", response_model=Envelope[dict[str, bool]])
async def delete_address(
    address_id: uuid.UUID,
    principal: CurrentPrincipal,
    service: Annotated[PatientService, Depends(get_patient_service)],
) -> Envelope[dict[str, bool]]:
    await service.delete_address(principal.user_id, address_id)
    return ok({"deleted": True})
