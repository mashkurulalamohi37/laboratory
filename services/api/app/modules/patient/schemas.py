"""Pydantic schemas for patients, family members, and addresses."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SexType = Literal["M", "F", "O"]
BloodGroupType = Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
RelationshipType = Literal["SELF", "FATHER", "MOTHER", "SPOUSE", "CHILD", "SIBLING", "OTHER"]
AddressLabelType = Literal["HOME", "WORK", "OTHER"]


class PatientCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    full_name_bn: str | None = Field(default=None, max_length=150)
    dob: date
    sex: SexType
    phone: str | None = Field(default=None, max_length=20)
    blood_group: BloodGroupType | None = None


class PatientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    full_name_bn: str | None = Field(default=None, max_length=150)
    dob: date | None = None
    sex: SexType | None = None
    phone: str | None = Field(default=None, max_length=20)
    blood_group: BloodGroupType | None = None


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_code: str
    full_name: str
    full_name_bn: str | None = None
    dob: date
    sex: str
    phone: str | None = None
    blood_group: str | None = None
    owner_user_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class FamilyMemberCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    full_name_bn: str | None = Field(default=None, max_length=150)
    dob: date
    sex: SexType
    relationship: RelationshipType = "OTHER"
    phone: str | None = Field(default=None, max_length=20)
    blood_group: BloodGroupType | None = None


class FamilyMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    patient_id: uuid.UUID
    relationship: str
    patient: PatientResponse


class AddressCreate(BaseModel):
    patient_id: uuid.UUID | None = None
    division_id: uuid.UUID | None = None
    district_id: uuid.UUID | None = None
    upazila_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    house: str = Field(min_length=1, max_length=100)
    road: str | None = Field(default=None, max_length=100)
    block: str | None = Field(default=None, max_length=50)
    landmark: str | None = Field(default=None, max_length=150)
    label: AddressLabelType = "HOME"
    is_default: bool = False


class AddressUpdate(BaseModel):
    division_id: uuid.UUID | None = None
    district_id: uuid.UUID | None = None
    upazila_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    house: str | None = Field(default=None, min_length=1, max_length=100)
    road: str | None = Field(default=None, max_length=100)
    block: str | None = Field(default=None, max_length=50)
    landmark: str | None = Field(default=None, max_length=150)
    label: AddressLabelType | None = None
    is_default: bool | None = None


class AddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    patient_id: uuid.UUID | None
    division_id: uuid.UUID | None
    district_id: uuid.UUID | None
    upazila_id: uuid.UUID | None
    area_id: uuid.UUID | None
    house: str
    road: str | None
    block: str | None
    landmark: str | None
    label: str
    is_default: bool
    created_at: datetime
