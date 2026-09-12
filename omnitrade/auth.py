from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_DNS, UUID, uuid5

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from omnitrade.config import get_settings


class LoginRequest(BaseModel):
    username: str
    password: str


class User(BaseModel):
    id: UUID
    username: str


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def authenticate(request: LoginRequest) -> User:
    # Course-local login. Production deployment must replace this with a hashed DB credential.
    allowed = {"mohammadamin": "omnitrade", "mehdi": "omnitrade", "demo": "demo"}
    if allowed.get(request.username) != request.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return User(id=uuid5(NAMESPACE_DNS, f"omnitrade:{request.username}"), username=request.username)


def issue_token(user: User) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user.id),
            "username": user.username,
            "iat": now,
            "exp": now + timedelta(hours=8),
        },
        get_settings().jwt_secret,
        algorithm="HS256",
    )


def current_user(token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
        return User(id=UUID(payload["sub"]), username=payload["username"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
