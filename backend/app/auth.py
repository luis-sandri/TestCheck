from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import User, UserRole, UserSession
from .schemas import LoginInput, RegisterInput, UserOutput


router = APIRouter(prefix="/auth", tags=["Autenticação"])
password_hasher = PasswordHasher()
settings = get_settings()


def serialize_user(user: User) -> UserOutput:
    return UserOutput(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
    )


def set_session_cookie(response: Response, user: User, db: Session) -> None:
    session_id = secrets.token_urlsafe(48)
    duration = timedelta(hours=settings.session_duration_hours)
    db.add(
        UserSession(
            id=session_id,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + duration,
        )
    )
    db.commit()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        max_age=int(duration.total_seconds()),
        httponly=True,
        secure=os.getenv("VERCEL") == "1",
        samesite="lax",
        path="/",
    )


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    session_id = request.cookies.get(settings.session_cookie_name)
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão não encontrada.")

    session = db.scalar(
        select(UserSession).where(
            UserSession.id == session_id,
            UserSession.expires_at > datetime.now(timezone.utc),
        )
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão expirada.")
    return session.user


@router.post("/register", response_model=UserOutput, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterInput, response: Response, db: Session = Depends(get_db)) -> UserOutput:
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=password_hasher.hash(payload.password),
        role=UserRole.RESPONSIBLE,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este e-mail já possui conta.") from error

    db.refresh(user)
    set_session_cookie(response, user, db)
    return serialize_user(user)


@router.post("/login", response_model=UserOutput)
def login(payload: LoginInput, response: Response, db: Session = Depends(get_db)) -> UserOutput:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos.")

    try:
        password_hasher.verify(user.password_hash, payload.password)
    except VerifyMismatchError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos.") from error

    set_session_cookie(response, user, db)
    return serialize_user(user)


@router.get("/me", response_model=UserOutput)
def me(current_user: User = Depends(get_current_user)) -> UserOutput:
    return serialize_user(current_user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> Response:
    session_id = request.cookies.get(settings.session_cookie_name)
    if session_id:
        session = db.get(UserSession, session_id)
        if session:
            db.delete(session)
            db.commit()
    response.delete_cookie(key=settings.session_cookie_name, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
