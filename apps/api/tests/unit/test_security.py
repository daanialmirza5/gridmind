import pytest
from fastapi import HTTPException

from app.core.security import (
    CurrentUser,
    Role,
    create_access_token,
    get_current_user,
    hash_password,
    require_role,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("correct-password")
    assert verify_password("correct-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_password_over_72_bytes_does_not_crash_bcrypt():
    long_password = "x" * 200
    hashed = hash_password(long_password)
    assert verify_password(long_password, hashed)


def test_access_token_roundtrip():
    token = create_access_token(subject="alice", role=Role.ANALYST.value)
    from fastapi.security import HTTPAuthorizationCredentials

    user = get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))
    assert user.username == "alice"
    assert user.role == Role.ANALYST.value


def test_get_current_user_rejects_missing_credentials():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(None)
    assert exc_info.value.status_code == 401


def test_require_role_allows_permitted_role():
    dependency = require_role(Role.ENERGY_MANAGER, Role.ADMIN)
    user = CurrentUser(username="bob", role=Role.ENERGY_MANAGER.value)
    assert dependency(user) is user


def test_require_role_rejects_unpermitted_role():
    dependency = require_role(Role.ENERGY_MANAGER, Role.ADMIN)
    user = CurrentUser(username="eve", role=Role.EXECUTIVE.value)
    with pytest.raises(HTTPException) as exc_info:
        dependency(user)
    assert exc_info.value.status_code == 403
