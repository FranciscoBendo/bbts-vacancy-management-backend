from datetime import datetime
from typing import Optional
from sqlalchemy import or_
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from app.models import (
    CandidateSuggestion, Candidate, Vacancy, CandidateSkill,
    IntegrationLog, IntegrationStatus, SuggestionStatus, User, AuditEvent,
)
from app.candidates.schemas import CandidateOut, CandidateExplanation, CandidateDetailOut, CandidateListOut
from app.synonyms.dictionary import normalize_skill
from app.imports.service import _upsert
from app.imports.schemas import CandidateIn

SCORE_THRESHOLD = 40.0


def _to_candidate_out(s: CandidateSuggestion) -> CandidateOut:
    exp = s.explanation_json
    return CandidateOut(
        id=s.id,
        vacancy_id=s.vacancy_id,
        candidate_id=s.candidate_id,
        full_name=s.candidate.full_name,
        headline=s.candidate.headline,
        location=s.candidate.location,
        score=s.score,
        explanation=CandidateExplanation(
            met_requirements=exp.get("met_requirements", 0),
            total_requirements=exp.get("total_requirements", 0),
            missing_mandatory=exp.get("missing_mandatory", []),
            strengths=exp.get("strengths", []),
            location_match=exp.get("location_match", True),
        ),
        status=s.status.value,
        rejection_reason=s.rejection_reason,
        rejected_at=s.rejected_at,
    )


def get_candidates(db: Session, vacancy_id: int) -> tuple[list[CandidateOut], list[CandidateOut], int]:
    if not db.query(Vacancy).filter(Vacancy.id == vacancy_id).first():
        raise HTTPException(status_code=404, detail="Vaga não encontrada")

    all_suggestions = (
        db.query(CandidateSuggestion)
        .options(joinedload(CandidateSuggestion.candidate))
        .filter(CandidateSuggestion.vacancy_id == vacancy_id)
        .order_by(CandidateSuggestion.score.desc())
        .all()
    )

    total_before_filter = len(all_suggestions)
    active = []
    rejected = []

    for s in all_suggestions:
        out = _to_candidate_out(s)
        if s.status == SuggestionStatus.REJECTED:
            rejected.append(out)
        elif s.score >= SCORE_THRESHOLD:
            active.append(out)
        else:
        # Abaixo do threshold mas ainda ACTIVE — inclui nos recusados com justificativa padrão
            out.rejection_reason = f"Score abaixo do mínimo de {SCORE_THRESHOLD:.0f}% (score obtido: {s.score:.1f}%)"
            rejected.append(out)
        # abaixo do threshold e ACTIVE são omitidos do ranking mas contados

    return active, rejected, total_before_filter


def reject_candidate(db: Session, vacancy_id: int, suggestion_id: int, reason: str, rh_user: User) -> CandidateOut:
    if not reason or not reason.strip():
        raise HTTPException(status_code=400, detail="Justificativa obrigatória para recusar candidato")

    suggestion = (
        db.query(CandidateSuggestion)
        .options(joinedload(CandidateSuggestion.candidate))
        .filter(
            CandidateSuggestion.id == suggestion_id,
            CandidateSuggestion.vacancy_id == vacancy_id,
        )
        .first()
    )
    if not suggestion:
        raise HTTPException(status_code=404, detail="Candidato não encontrado nesta vaga")
    if suggestion.status == SuggestionStatus.REJECTED:
        raise HTTPException(status_code=400, detail="Candidato já foi recusado")

    suggestion.status = SuggestionStatus.REJECTED
    suggestion.rejection_reason = reason.strip()
    suggestion.rejected_at = datetime.utcnow()
    suggestion.rejected_by_id = rh_user.id

    db.commit()
    db.refresh(suggestion)
    return _to_candidate_out(suggestion)


def get_candidate_detail(db: Session, candidate_id: int) -> CandidateDetailOut:
    c = db.query(Candidate).options(
        joinedload(Candidate.skills), joinedload(Candidate.experiences),
        joinedload(Candidate.educations), joinedload(Candidate.languages),
        joinedload(Candidate.certifications),
    ).filter(Candidate.id == candidate_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidato não encontrado")
    return CandidateDetailOut.model_validate(c)


def list_candidates(db: Session, skill: Optional[str] = None, location: Optional[str] = None) -> list:
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
        result.append({
            "id": c.id, "full_name": c.full_name, "headline": c.headline,
            "location": c.location, "email": c.email,
            "skills_summary": [s.name for s in c.skills[:5]],
            "created_at": c.created_at,
        })
    return result


def import_from_pdf_data(db: Session, extracted: dict, filename: str) -> tuple:
    try:
        candidate = _upsert(db, CandidateIn(**extracted))
        log = IntegrationLog(source="PDF", filename=filename, status=IntegrationStatus.SUCCESS,
                             total_records=1, success_count=1, error_count=0)
        db.add(log); db.commit(); db.refresh(candidate); db.refresh(log)
        return candidate, log
    except Exception as e:
        db.rollback()
        log = IntegrationLog(source="PDF", filename=filename, status=IntegrationStatus.FAILED,
                             total_records=1, success_count=0, error_count=1,
                             errors_json=[{"row": 1, "message": str(e)}])
        db.add(log); db.commit()
        raise

def anonymize_candidate(db: Session, candidate_id: int, rh_user: User) -> dict:
    """
    Anonimiza os dados pessoais do candidato conforme LGPD.
    Não apaga o registro — mantém o histórico de scores anonimizado.
    """
    c = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidato não encontrado")

    anon_id = f"anonimizado-{candidate_id}"

    c.full_name = f"Candidato Removido #{candidate_id}"
    c.email = None
    c.linkedin_url = None
    c.headline = "Dados removidos a pedido do titular (LGPD)"
    c.location = ""

    # Remove dados sensíveis das sub-tabelas
    for skill in c.skills: db.delete(skill)
    for exp in c.experiences: db.delete(exp)
    for edu in c.educations: db.delete(edu)
    for lang in c.languages: db.delete(lang)
    for cert in c.certifications: db.delete(cert)

    db.add(AuditEvent(
        actor_user_id=rh_user.id,
        action="CANDIDATE_ANONYMIZED_LGPD",
        entity_type="Candidate",
        entity_id=candidate_id,
        metadata_json={"reason": "Solicitação de remoção de dados pessoais (LGPD)"},
    ))

    db.commit()
    return {"message": f"Dados do candidato #{candidate_id} foram anonimizados com sucesso."}