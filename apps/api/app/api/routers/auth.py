from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import GridMindError
from app.core.security import create_access_token, verify_password
from app.domain.system import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    full_name: str
    role: str


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise GridMindError("INVALID_CREDENTIALS", "Invalid username or password", status_code=401)
    token = create_access_token(subject=user.username, role=user.role)
    return LoginResponse(access_token=token, username=user.username, full_name=user.full_name, role=user.role)


@router.get("/demo-users")
def demo_users(db: Session = Depends(get_db)):
    """Lists demo accounts so the frontend login page can offer one-click role switching."""
    users = db.query(User).all()
    return [{"username": u.username, "full_name": u.full_name, "role": u.role} for u in users]
