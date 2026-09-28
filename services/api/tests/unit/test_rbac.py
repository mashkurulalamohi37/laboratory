import uuid

import pytest

from app.core.errors import PermissionDenied
from app.modules.auth.permissions import (
    PRIVILEGED_ROLES,
    ROLE_DEFAULTS,
    STAFF_ROLES,
    P,
    Role,
    ScopeType,
)
from app.modules.auth.principal import Principal, RoleGrant

BRANCH_A, BRANCH_B = uuid.uuid4(), uuid.uuid4()


def _principal(perms: dict[P, set[tuple[ScopeType, uuid.UUID | None]]]) -> Principal:
    return Principal(
        user_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        is_staff=True,
        status="ACTIVE",
        grants=(RoleGrant("BRANCH_MANAGER", "BRANCH", BRANCH_A),),
        permissions={
            p.value: frozenset((st.value, sid) for st, sid in scopes) for p, scopes in perms.items()
        },
    )


def test_global_grant_covers_every_scope() -> None:
    p = _principal({P.BOOKING_VIEW: {(ScopeType.GLOBAL, None)}})
    assert p.has(P.BOOKING_VIEW)
    assert p.has(P.BOOKING_VIEW, ScopeType.BRANCH, BRANCH_B)
    assert p.scope_ids(P.BOOKING_VIEW, ScopeType.BRANCH) is None


def test_scoped_grant_only_covers_its_scope() -> None:
    p = _principal({P.BOOKING_VIEW: {(ScopeType.BRANCH, BRANCH_A)}})
    assert p.has(P.BOOKING_VIEW)  # route-level: held somewhere
    assert p.has(P.BOOKING_VIEW, ScopeType.BRANCH, BRANCH_A)
    assert not p.has(P.BOOKING_VIEW, ScopeType.BRANCH, BRANCH_B)
    assert p.scope_ids(P.BOOKING_VIEW, ScopeType.BRANCH) == {BRANCH_A}
    with pytest.raises(PermissionDenied):
        p.require(P.BOOKING_VIEW, ScopeType.BRANCH, BRANCH_B)


def test_missing_permission_denied() -> None:
    p = _principal({})
    assert not p.has(P.RESULT_VERIFY)
    with pytest.raises(PermissionDenied):
        p.require(P.RESULT_VERIFY)


def test_principal_cache_roundtrip_preserves_scopes() -> None:
    p = _principal({P.BOOKING_VIEW: {(ScopeType.BRANCH, BRANCH_A), (ScopeType.GLOBAL, None)}})
    restored = Principal.from_json(p.to_json(), p.session_id)
    assert restored == p


def test_role_catalogue_invariants() -> None:
    assert set(ROLE_DEFAULTS) == set(Role)
    assert ROLE_DEFAULTS[Role.SUPER_ADMIN] == frozenset(P)
    assert ROLE_DEFAULTS[Role.PATIENT] == frozenset()
    assert Role.PATIENT not in STAFF_ROLES
    assert {Role.SUPER_ADMIN, Role.ADMIN} == PRIVILEGED_ROLES


def test_clinical_safety_separation_of_duties() -> None:
    # Only pathologists (and super admins) verify results; admins cannot.
    verifiers = {r for r, perms in ROLE_DEFAULTS.items() if P.RESULT_VERIFY in perms}
    assert verifiers == {Role.SUPER_ADMIN, Role.PATHOLOGIST}
    # Collectors can never see results or reports.
    for perm in (P.RESULT_VIEW, P.REPORT_VIEW, P.REPORT_DOWNLOAD):
        assert perm not in ROLE_DEFAULTS[Role.PHLEBOTOMIST]
    # Corporate admins get no clinical permissions by role (consent-gated later).
    assert not {P.RESULT_VIEW, P.REPORT_VIEW} & ROLE_DEFAULTS[Role.CORPORATE_ADMIN]
