"""Organizações e seleção do espaço de trabalho ativo."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .auth import get_current_user, serialize_user
from .database import get_db
from .models import Organization, OrganizationMembership, OrganizationRole, User
from .schemas import (
    OrganizationCreateInput,
    OrganizationJoinInput,
    OrganizationOutput,
    OrganizationSelectInput,
    PublicOrganizationOutput,
    UserOutput,
)


router = APIRouter(prefix="/organizations", tags=["Organizações"])


def membership_query(user_id: str):
    return (
        select(OrganizationMembership)
        .options(selectinload(OrganizationMembership.organization))
        .where(OrganizationMembership.user_id == user_id)
        .order_by(Organization.name.asc())
        .join(OrganizationMembership.organization)
    )


def serialize_organization(membership: OrganizationMembership) -> OrganizationOutput:
    return OrganizationOutput(
        id=membership.organization.id,
        name=membership.organization.name,
        role=membership.role,
    )


def get_current_organization(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Organization:
    if not current_user.active_organization_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Selecione ou crie uma organização antes de acessar os dados.",
        )
    membership = db.scalar(
        membership_query(current_user.id).where(
            OrganizationMembership.organization_id == current_user.active_organization_id
        )
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não participa da organização selecionada.")
    return membership.organization


@router.get("/public", response_model=list[PublicOrganizationOutput])
def list_public_organizations(db: Session = Depends(get_db)) -> list[PublicOrganizationOutput]:
    """Lista nomes para o fluxo simples de entrada na organização."""
    organizations = db.scalars(select(Organization).order_by(Organization.name.asc())).all()
    return [PublicOrganizationOutput(id=organization.id, name=organization.name) for organization in organizations]


@router.get("", response_model=list[OrganizationOutput])
def list_my_organizations(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[OrganizationOutput]:
    return [serialize_organization(item) for item in db.scalars(membership_query(current_user.id)).all()]


@router.post("", response_model=UserOutput, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreateInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserOutput:
    organization = Organization(name=payload.name)
    db.add(organization)
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe uma organização com esse nome.") from error
    db.add(
        OrganizationMembership(
            organization_id=organization.id,
            user_id=current_user.id,
            role=OrganizationRole.OWNER,
        )
    )
    current_user.active_organization_id = organization.id
    db.commit()
    db.refresh(current_user)
    return serialize_user(current_user, db)


@router.post("/join", response_model=UserOutput)
def join_organization(
    payload: OrganizationJoinInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserOutput:
    organization = db.get(Organization, payload.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organização não encontrada.")
    membership = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization.id,
            OrganizationMembership.user_id == current_user.id,
        )
    )
    if membership is None:
        db.add(
            OrganizationMembership(
                organization_id=organization.id,
                user_id=current_user.id,
                role=OrganizationRole.MEMBER,
            )
        )
    current_user.active_organization_id = organization.id
    db.commit()
    db.refresh(current_user)
    return serialize_user(current_user, db)


@router.post("/select", response_model=UserOutput)
def select_organization(
    payload: OrganizationSelectInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserOutput:
    membership = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == payload.organization_id,
            OrganizationMembership.user_id == current_user.id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não participa dessa organização.")
    current_user.active_organization_id = payload.organization_id
    db.commit()
    db.refresh(current_user)
    return serialize_user(current_user, db)
