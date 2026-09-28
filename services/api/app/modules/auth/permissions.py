"""Permission and role catalogue.

Permission codes are defined in code (they gate code paths). The role → permission
mapping below is the *seed default*; SUPER_ADMIN can edit mappings at runtime, except
for SUPER_ADMIN itself, which always holds every permission.
"""

from __future__ import annotations

from enum import StrEnum


class P(StrEnum):
    # identity & access
    USER_MANAGE = "user:manage"
    ROLE_MANAGE = "role:manage"
    AUDIT_VIEW = "audit:view"
    SETTINGS_MANAGE = "settings:manage"
    # patients
    PATIENT_VIEW = "patient:view"
    PATIENT_CREATE = "patient:create"
    PATIENT_UPDATE = "patient:update"
    # catalog
    TEST_VIEW = "test:view"
    TEST_CREATE = "test:create"
    TEST_UPDATE = "test:update"
    TEST_DELETE = "test:delete"
    PACKAGE_MANAGE = "package:manage"
    PRICE_MANAGE = "price:manage"
    CENTRE_MANAGE = "centre:manage"
    SLOT_MANAGE = "slot:manage"
    # booking
    BOOKING_VIEW = "booking:view"
    BOOKING_CREATE = "booking:create"
    BOOKING_UPDATE = "booking:update"
    BOOKING_CANCEL = "booking:cancel"
    # collection & samples
    COLLECTION_VIEW = "collection:view"
    COLLECTION_ASSIGN = "collection:assign"
    COLLECTION_PERFORM = "collection:perform"
    SAMPLE_VIEW = "sample:view"
    SAMPLE_UPDATE = "sample:update"
    SAMPLE_TRANSFER = "sample:transfer"
    SAMPLE_RECEIVE = "sample:receive"
    SAMPLE_REJECT = "sample:reject"
    # lab
    LAB_VIEW = "lab:view"
    RESULT_VIEW = "result:view"
    RESULT_ENTER = "result:enter"
    RESULT_EDIT = "result:edit"
    RESULT_VERIFY = "result:verify"
    REPORT_VIEW = "report:view"
    REPORT_GENERATE = "report:generate"
    REPORT_DOWNLOAD = "report:download"
    REPORT_AMEND = "report:amend"
    # money
    PAYMENT_VIEW = "payment:view"
    PAYMENT_CREATE = "payment:create"
    REFUND_CREATE = "refund:create"
    REFUND_APPROVE = "refund:approve"
    COUPON_MANAGE = "coupon:manage"
    INVOICE_VIEW = "invoice:view"
    INVOICE_MANAGE = "invoice:manage"
    # operations
    INVENTORY_VIEW = "inventory:view"
    INVENTORY_UPDATE = "inventory:update"
    PURCHASE_MANAGE = "purchase:manage"
    PARTNER_MANAGE = "partner:manage"
    CORPORATE_MANAGE = "corporate:manage"
    CMS_MANAGE = "cms:manage"
    NOTIFICATION_MANAGE = "notification:manage"
    SUPPORT_VIEW = "support:view"
    SUPPORT_MANAGE = "support:manage"
    ANALYTICS_VIEW = "analytics:view"


class Role(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    BRANCH_MANAGER = "BRANCH_MANAGER"
    LAB_MANAGER = "LAB_MANAGER"
    PATHOLOGIST = "PATHOLOGIST"
    DOCTOR = "DOCTOR"
    LAB_TECHNICIAN = "LAB_TECHNICIAN"
    PHLEBOTOMIST = "PHLEBOTOMIST"
    RECEPTIONIST = "RECEPTIONIST"
    ACCOUNTANT = "ACCOUNTANT"
    CUSTOMER_SUPPORT = "CUSTOMER_SUPPORT"
    CONTENT_MANAGER = "CONTENT_MANAGER"
    INVENTORY_MANAGER = "INVENTORY_MANAGER"
    CORPORATE_ADMIN = "CORPORATE_ADMIN"
    PARTNER_ADMIN = "PARTNER_ADMIN"
    PATIENT = "PATIENT"


class ScopeType(StrEnum):
    GLOBAL = "GLOBAL"
    BRANCH = "BRANCH"
    LAB = "LAB"
    CORPORATE = "CORPORATE"
    PARTNER = "PARTNER"


#: Roles that are staff (password + 2FA login, console access).
STAFF_ROLES = frozenset(Role) - {Role.PATIENT}

#: Roles only a SUPER_ADMIN may grant.
PRIVILEGED_ROLES = frozenset({Role.SUPER_ADMIN, Role.ADMIN})

PERMISSION_DESCRIPTIONS: dict[P, str] = {p: p.value.replace(":", " — ") for p in P}

_CATALOG_READ = {P.TEST_VIEW}
_LAB_READ = {P.LAB_VIEW, P.SAMPLE_VIEW, P.RESULT_VIEW, P.REPORT_VIEW, P.PATIENT_VIEW}

ROLE_DEFAULTS: dict[Role, frozenset[P]] = {
    Role.SUPER_ADMIN: frozenset(P),
    Role.ADMIN: frozenset(P) - {P.ROLE_MANAGE, P.SETTINGS_MANAGE, P.RESULT_VERIFY, P.REPORT_AMEND},
    Role.BRANCH_MANAGER: frozenset(
        {
            *_CATALOG_READ,
            P.PATIENT_VIEW,
            P.PATIENT_CREATE,
            P.PATIENT_UPDATE,
            P.BOOKING_VIEW,
            P.BOOKING_CREATE,
            P.BOOKING_UPDATE,
            P.BOOKING_CANCEL,
            P.COLLECTION_VIEW,
            P.COLLECTION_ASSIGN,
            P.SAMPLE_VIEW,
            P.SLOT_MANAGE,
            P.PAYMENT_VIEW,
            P.INVOICE_VIEW,
            P.INVENTORY_VIEW,
            P.SUPPORT_VIEW,
            P.ANALYTICS_VIEW,
            P.REPORT_VIEW,
        }
    ),
    Role.LAB_MANAGER: frozenset(
        {
            *_CATALOG_READ,
            *_LAB_READ,
            P.SAMPLE_UPDATE,
            P.SAMPLE_RECEIVE,
            P.SAMPLE_REJECT,
            P.SAMPLE_TRANSFER,
            P.RESULT_ENTER,
            P.RESULT_EDIT,
            P.REPORT_GENERATE,
            P.INVENTORY_VIEW,
            P.INVENTORY_UPDATE,
            P.ANALYTICS_VIEW,
        }
    ),
    Role.PATHOLOGIST: frozenset(
        {
            *_CATALOG_READ,
            *_LAB_READ,
            P.RESULT_EDIT,
            P.RESULT_VERIFY,
            P.REPORT_GENERATE,
            P.REPORT_DOWNLOAD,
            P.REPORT_AMEND,
        }
    ),
    Role.DOCTOR: frozenset({*_CATALOG_READ, P.PATIENT_VIEW, P.REPORT_VIEW, P.REPORT_DOWNLOAD}),
    Role.LAB_TECHNICIAN: frozenset(
        {
            *_CATALOG_READ,
            *_LAB_READ,
            P.SAMPLE_UPDATE,
            P.SAMPLE_RECEIVE,
            P.SAMPLE_REJECT,
            P.RESULT_ENTER,
        }
    ),
    Role.PHLEBOTOMIST: frozenset(
        {
            P.COLLECTION_VIEW,
            P.COLLECTION_PERFORM,
            P.SAMPLE_UPDATE,
            P.SAMPLE_REJECT,
        }
    ),
    Role.RECEPTIONIST: frozenset(
        {
            *_CATALOG_READ,
            P.PATIENT_VIEW,
            P.PATIENT_CREATE,
            P.PATIENT_UPDATE,
            P.BOOKING_VIEW,
            P.BOOKING_CREATE,
            P.BOOKING_UPDATE,
            P.BOOKING_CANCEL,
            P.PAYMENT_VIEW,
            P.PAYMENT_CREATE,
            P.SAMPLE_VIEW,
            P.SAMPLE_UPDATE,
            P.REPORT_VIEW,
            P.REPORT_DOWNLOAD,
        }
    ),
    Role.ACCOUNTANT: frozenset(
        {
            *_CATALOG_READ,
            P.PRICE_MANAGE,
            P.PAYMENT_VIEW,
            P.REFUND_CREATE,
            P.REFUND_APPROVE,
            P.INVOICE_VIEW,
            P.INVOICE_MANAGE,
            P.ANALYTICS_VIEW,
            P.BOOKING_VIEW,
        }
    ),
    Role.CUSTOMER_SUPPORT: frozenset(
        {
            *_CATALOG_READ,
            P.PATIENT_VIEW,
            P.BOOKING_VIEW,
            P.BOOKING_UPDATE,
            P.BOOKING_CANCEL,
            P.PAYMENT_VIEW,
            P.REFUND_CREATE,
            P.SUPPORT_VIEW,
            P.SUPPORT_MANAGE,
            P.SAMPLE_VIEW,
        }
    ),
    Role.CONTENT_MANAGER: frozenset({*_CATALOG_READ, P.CMS_MANAGE, P.NOTIFICATION_MANAGE}),
    Role.INVENTORY_MANAGER: frozenset({P.INVENTORY_VIEW, P.INVENTORY_UPDATE, P.PURCHASE_MANAGE}),
    Role.CORPORATE_ADMIN: frozenset({P.BOOKING_VIEW, P.BOOKING_CREATE, P.INVOICE_VIEW}),
    Role.PARTNER_ADMIN: frozenset(
        {
            *_CATALOG_READ,
            P.PATIENT_VIEW,
            P.PATIENT_CREATE,
            P.BOOKING_VIEW,
            P.BOOKING_CREATE,
            P.SAMPLE_VIEW,
            P.INVOICE_VIEW,
        }
    ),
    # Patients act on their own data through ownership checks, not staff permissions.
    Role.PATIENT: frozenset(),
}

ROLE_NAMES: dict[Role, str] = {r: r.value.replace("_", " ").title() for r in Role}
