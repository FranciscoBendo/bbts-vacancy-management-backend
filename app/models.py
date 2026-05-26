import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Enum, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class RoleEnum(str, enum.Enum):
    REQUESTER = "REQUESTER"
    RH = "RH"

class VacancyStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IN_PROGRESS = "IN_PROGRESS"
    FINALIZED = "FINALIZED"

class RequirementType(str, enum.Enum):
    SKILL = "SKILL"
    LANGUAGE = "LANGUAGE"
    CERTIFICATION = "CERTIFICATION"
    EDUCATION = "EDUCATION"
    COMPANY = "COMPANY"
    LOCATION = "LOCATION"

class DecisionEnum(str, enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class PriorityEnum(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class IntegrationStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"

class SuggestionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), nullable=False)
    vacancies: Mapped[list["Vacancy"]] = relationship("Vacancy", back_populates="requester")
    decisions: Mapped[list["ApprovalDecision"]] = relationship("ApprovalDecision", back_populates="rh_user")
    audit_events: Mapped[list["AuditEvent"]] = relationship("AuditEvent", back_populates="actor")

class Vacancy(Base):
    __tablename__ = "vacancies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    priority: Mapped[PriorityEnum] = mapped_column(Enum(PriorityEnum), default=PriorityEnum.MEDIUM)
    status: Mapped[VacancyStatus] = mapped_column(Enum(VacancyStatus), default=VacancyStatus.DRAFT)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    requester: Mapped["User"] = relationship("User", back_populates="vacancies")
    requirements: Mapped[list["Requirement"]] = relationship("Requirement", back_populates="vacancy", cascade="all, delete-orphan")
    decisions: Mapped[list["ApprovalDecision"]] = relationship("ApprovalDecision", back_populates="vacancy")
    suggestions: Mapped[list["CandidateSuggestion"]] = relationship("CandidateSuggestion", back_populates="vacancy", cascade="all, delete-orphan")

class Requirement(Base):
    __tablename__ = "requirements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id"), nullable=False)
    type: Mapped[RequirementType] = mapped_column(Enum(RequirementType), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    level: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    vacancy: Mapped["Vacancy"] = relationship("Vacancy", back_populates="requirements")

class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id"), nullable=False)
    rh_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    decision: Mapped[DecisionEnum] = mapped_column(Enum(DecisionEnum), nullable=False)
    justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    vacancy: Mapped["Vacancy"] = relationship("Vacancy", back_populates="decisions")
    rh_user: Mapped["User"] = relationship("User", back_populates="decisions")

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actor: Mapped["User"] = relationship("User", back_populates="audit_events")

class Candidate(Base):
    __tablename__ = "candidates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    headline: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, unique=True)
    location: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    skills: Mapped[list["CandidateSkill"]] = relationship("CandidateSkill", back_populates="candidate", cascade="all, delete-orphan")
    experiences: Mapped[list["CandidateExperience"]] = relationship("CandidateExperience", back_populates="candidate", cascade="all, delete-orphan")
    educations: Mapped[list["CandidateEducation"]] = relationship("CandidateEducation", back_populates="candidate", cascade="all, delete-orphan")
    languages: Mapped[list["CandidateLanguage"]] = relationship("CandidateLanguage", back_populates="candidate", cascade="all, delete-orphan")
    certifications: Mapped[list["CandidateCertification"]] = relationship("CandidateCertification", back_populates="candidate", cascade="all, delete-orphan")
    suggestions: Mapped[list["CandidateSuggestion"]] = relationship("CandidateSuggestion", back_populates="candidate")

class CandidateSkill(Base):
    __tablename__ = "candidate_skills"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    level: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    years_experience: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="skills")

class CandidateExperience(Base):
    __tablename__ = "candidate_experiences"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    company: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    start_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current: Mapped[bool] = mapped_column(Boolean, default=False)
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="experiences")

class CandidateEducation(Base):
    __tablename__ = "candidate_educations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    institution: Mapped[str] = mapped_column(String(200), nullable=False)
    course: Mapped[str] = mapped_column(String(200), nullable=False)
    degree: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    graduation_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="educations")

class CandidateLanguage(Base):
    __tablename__ = "candidate_languages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="languages")

class CandidateCertification(Base):
    __tablename__ = "candidate_certifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    issuer: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="certifications")

class CandidateSuggestion(Base):
    __tablename__ = "candidate_suggestions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id"), nullable=False)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    explanation_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Sprint 4 — status de recusa
    status: Mapped[SuggestionStatus] = mapped_column(Enum(SuggestionStatus), default=SuggestionStatus.ACTIVE, nullable=False)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejected_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    vacancy: Mapped["Vacancy"] = relationship("Vacancy", back_populates="suggestions")
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="suggestions")

class IntegrationLog(Base):
    __tablename__ = "integration_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    filename: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    status: Mapped[IntegrationStatus] = mapped_column(Enum(IntegrationStatus), nullable=False)
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    errors_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
