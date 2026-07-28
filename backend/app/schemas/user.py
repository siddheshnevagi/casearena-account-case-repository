from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class SignupResponse(BaseModel):
    id: int
    email: EmailStr
    is_verified: bool
    verification_token: str
    verification_token_note: str = "dev_only: emailed in production, see ARCHITECTURE.md ADR-04"


class VerifyRequest(BaseModel):
    token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_admin: bool
    is_verified: bool

    model_config = {"from_attributes": True}


class AccountDeletionResult(BaseModel):
    message: str
    cases_anonymized: int
    cases_deleted: int
