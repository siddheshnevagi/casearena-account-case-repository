from pydantic import BaseModel, Field

from app.models.profile import TargetFirmType
from app.schemas.case import CaseOut


class OnboardingRequest(BaseModel):
    target_firm_type: TargetFirmType
    case_preferences: list[str] = Field(default_factory=list)


class ProfileUpdateRequest(BaseModel):
    target_firm_type: TargetFirmType | None = None
    case_preferences: list[str] | None = None


class ProfileOut(BaseModel):
    user_id: int
    target_firm_type: TargetFirmType | None
    case_preferences: list[str]
    onboarding_completed: bool

    model_config = {"from_attributes": True}


class DashboardOut(BaseModel):
    profile: ProfileOut
    recommended_cases: list[CaseOut]
