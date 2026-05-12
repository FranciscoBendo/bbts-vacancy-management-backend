from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class CandidateExplanation(BaseModel):
    met_requirements: int
    total_requirements: int
    missing_mandatory: list[str]
    strengths: list[str]
    location_match: bool = True

class CandidateOut(BaseModel):
    id: int
    vacancy_id: int
    candidate_id: int
    full_name: str
    headline: str
    location: str
    score: float
    explanation: CandidateExplanation
    model_config = {"from_attributes": True}

class SkillOut(BaseModel):
    id: int; name: str; level: Optional[str]; years_experience: Optional[float]
    model_config = {"from_attributes": True}

class ExperienceOut(BaseModel):
    id: int; company: str; role: str; start_year: Optional[int]; end_year: Optional[int]; current: bool
    model_config = {"from_attributes": True}

class EducationOut(BaseModel):
    id: int; institution: str; course: str; degree: Optional[str]; graduation_year: Optional[int]
    model_config = {"from_attributes": True}

class LanguageOut(BaseModel):
    id: int; name: str; level: Optional[str]
    model_config = {"from_attributes": True}

class CertificationOut(BaseModel):
    id: int; name: str; issuer: Optional[str]; year: Optional[int]
    model_config = {"from_attributes": True}

class CandidateDetailOut(BaseModel):
    id: int; full_name: str; headline: str; email: Optional[str]; location: str
    linkedin_url: Optional[str]; created_at: datetime
    skills: list[SkillOut] = []; experiences: list[ExperienceOut] = []
    educations: list[EducationOut] = []; languages: list[LanguageOut] = []
    certifications: list[CertificationOut] = []
    model_config = {"from_attributes": True}

class CandidateListOut(BaseModel):
    """Item na listagem geral de candidatos."""
    id: int
    full_name: str
    headline: str
    location: str
    email: Optional[str]
    skills_summary: list[str]
    created_at: datetime
    model_config = {"from_attributes": True}