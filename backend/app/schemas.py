from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from .models import AuditStatus, ChecklistResult, UserRole


class RegisterInput(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("email")
    @classmethod
    def clean_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise ValueError("Informe um e-mail válido.")
        return email


class LoginInput(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=1, max_length=72)

    @field_validator("email")
    @classmethod
    def clean_email(cls, value: str) -> str:
        return value.strip().lower()


class UserOutput(BaseModel):
    id: str
    full_name: str
    email: str
    role: UserRole


class TestCaseInput(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    responsible_email: str = Field(default="", max_length=255)
    description: str = Field(default="", max_length=10_000)
    preconditions: str = Field(default="", max_length=10_000)
    steps: str = Field(default="", max_length=20_000)
    test_data: str = Field(default="", max_length=10_000)
    expected_result: str = Field(default="", max_length=10_000)
    approval_criteria: str = Field(default="", max_length=10_000)

    @field_validator(
        "title",
        "responsible_email",
        "description",
        "preconditions",
        "steps",
        "test_data",
        "expected_result",
        "approval_criteria",
    )
    @classmethod
    def trim_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("responsible_email")
    @classmethod
    def clean_responsible_email(cls, value: str) -> str:
        email = value.strip().lower()
        if email and ("@" not in email or email.startswith("@") or email.endswith("@")):
            raise ValueError("Informe um e-mail válido para o responsável.")
        return email


class TestCaseOutput(BaseModel):
    id: str
    code: str
    title: str
    description: str | None
    preconditions: str | None
    steps: str | None
    test_data: str | None
    expected_result: str | None
    approval_criteria: str | None
    author_id: str
    author_name: str
    responsible_email: str
    created_at: datetime
    updated_at: datetime


class AuditStartInput(BaseModel):
    test_case_id: str = Field(min_length=1, max_length=36)


class AuditItemOutput(BaseModel):
    checklist_code: str
    checklist_label: str
    result: ChecklistResult | None
    note: str | None


class AuditOutput(BaseModel):
    id: str
    test_case_id: str
    test_case_code: str
    test_case_title: str
    auditor_name: str
    status: AuditStatus
    adherence_percentage: int | None
    nonconformity_count: int
    items: list[AuditItemOutput]
    created_at: datetime
    completed_at: datetime | None
