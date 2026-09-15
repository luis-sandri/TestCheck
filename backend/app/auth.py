from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .config import get_settings
from .database import get_db
from .models import Organization, OrganizationMembership, OrganizationRole, User, UserRole, UserSession
from .schemas import OrganizationOutput
from .schemas import LoginInput, RegisterInput, UserOutput


router = APIRouter(prefix="/auth", tags=["Autenticação"])
password_hasher = PasswordHasher()
settings = get_settings()


def serialize_user(user: User, db: Session) -> UserOutput:
    memberships = db.scalars(
        select(OrganizationMembership)
        .options(selectinload(OrganizationMembership.organization))
        .where(OrganizationMembership.user_id == user.id)
        .join(OrganizationMembership.organization)
        .order_by(Organization.name.asc())
    ).all()
    organizations = [
        OrganizationOutput(id=item.organization.id, name=item.organization.name, role=item.role)
        for item in memberships
    ]
    active_organization = next(
        (organization for organization in organizations if organization.id == user.active_organization_id), None
    )
    return UserOutput(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        active_organization=active_organization,
        organizations=organizations,
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
        db.flush()
        if payload.organization_name:
            organization = Organization(name=payload.organization_name)
            db.add(organization)
            db.flush()
            membership_role = OrganizationRole.OWNER
        else:
            organization = db.get(Organization, payload.organization_id)
            if organization is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organização não encontrada.")
            membership_role = OrganizationRole.MEMBER
        db.add(
            OrganizationMembership(
                organization_id=organization.id,
                user_id=user.id,
                role=membership_role,
            )
        )
        user.active_organization_id = organization.id
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="O e-mail ou o nome da organização já está em uso.") from error

    db.refresh(user)
    set_session_cookie(response, user, db)
    return serialize_user(user, db)


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
    return serialize_user(user, db)


@router.get("/me", response_model=UserOutput)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserOutput:
    return serialize_user(current_user, db)


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
