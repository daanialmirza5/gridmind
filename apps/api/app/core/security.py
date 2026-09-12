"""Auth primitives: password hashing, JWT issuance/verification, and RBAC.

Roles form the enforcement surface for every mutating/sensitive endpoint.
Authorization is checked server-side via `require_role`; the frontend may
also hide controls, but that is UX only and must never be the sole gate.
"""

from datetime import datetime, timedelta, timezone
from enum import Enum

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


class Role(str, Enum):
    ENERGY_MANAGER = "ENERGY_MANAGER"
    FACILITY_MANAGER = "FACILITY_MANAGER"
    ANALYST = "ANALYST"
    EXECUTIVE = "EXECUTIVE"
    ADMIN = "ADMIN"


# Roles allowed to approve/reject recommendations and mutate configuration.
WRITE_ROLES = {Role.ENERGY_MANAGER, Role.FACILITY_MANAGER, Role.ADMIN}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class CurrentUser:
    def __init__(self, username: str, role: str):
        self.username = username
        self.role = role


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    username = payload.get("sub")
    role = payload.get("role")
    if not username or not role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return CurrentUser(username=username, role=role)


def require_role(*allowed: Role):
    allowed_values = {r.value for r in allowed}

    def _dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not permitted to perform this action",
            )
        return user

    return _dependency
