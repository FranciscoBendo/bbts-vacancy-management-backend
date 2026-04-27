from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from app.models import CandidateSuggestion, Candidate, CandidateSkill, Vacancy
from app.candidates.schemas import CandidateOut, CandidateExplanation, CandidateDetailOut, CandidateListOut
from app.synonyms.dictionary import normalize_skill

def get_candidates(db: Session, vacancy_id: int) -> list[CandidateOut]:
    if not db.query(Vacancy).filter(Vacancy.id == vacancy_id).first():
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    suggestions = db.query(CandidateSuggestion).options(joinedload(CandidateSuggestion.candidate)).filter(CandidateSuggestion.vacancy_id == vacancy_id).order_by(CandidateSuggestion.score.desc()).all()
    result = []
    for s in suggestions:
        exp = s.explanation_json
        result.append(CandidateOut(
            id=s.id, vacancy_id=s.vacancy_id, candidate_id=s.candidate_id,
            full_name=s.candidate.full_name, headline=s.candidate.headline,
            location=s.candidate.location, score=s.score,
            explanation=CandidateExplanation(
                met_requirements=exp.get("met_requirements", 0),
                total_requirements=exp.get("total_requirements", 0),
                missing_mandatory=exp.get("missing_mandatory", []),
                strengths=exp.get("strengths", []),
                location_match=exp.get("location_match", True),
            ),
        ))
    return result

def list_candidates(db: Session, skill: Optional[str] = None, location: Optional[str] = None) -> list[CandidateListOut]:
    q = db.query(Candidate).options(joinedload(Candidate.skills))
    if location:
        q = q.filter(Candidate.location.ilike(f"%{location}%"))
    if skill:
        normalized = normalize_skill(skill)
        q = q.filter(Candidate.skills.any(or_(
            CandidateSkill.name.ilike(f"%{skill}%"),
            CandidateSkill.name.ilike(f"%{normalized}%"),
        )))
    result = []
    for c in q.order_by(Candidate.created_at.desc()).all():
        result.append(CandidateListOut(
            id=c.id, full_name=c.full_name, headline=c.headline,
            location=c.location, email=c.email,
            skills_summary=[s.name for s in c.skills[:5]],
            created_at=c.created_at,
        ))
    return result

def get_candidate_detail(db: Session, candidate_id: int) -> CandidateDetailOut:
    c = db.query(Candidate).options(
        joinedload(Candidate.skills), joinedload(Candidate.experiences),
        joinedload(Candidate.educations), joinedload(Candidate.languages),
        joinedload(Candidate.certifications),
    ).filter(Candidate.id == candidate_id).first()
    if not c: raise HTTPException(status_code=404, detail="Candidato não encontrado")
    return CandidateDetailOut.model_validate(c)
