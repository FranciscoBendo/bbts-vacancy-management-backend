from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models import (
    Vacancy, Candidate, CandidateSuggestion, ApprovalDecision,
    AuditEvent, VacancyStatus, DecisionEnum, SuggestionStatus
)
from app.scoring.engine import calculate_score
from app.candidates.service import SCORE_THRESHOLD

def _audit(db, actor_id, action, vacancy_id, metadata=None):
    db.add(AuditEvent(actor_user_id=actor_id, action=action, entity_type="Vacancy",
                      entity_id=vacancy_id, metadata_json=metadata or {}))

def list_pending(db: Session) -> list[Vacancy]:
    return db.query(Vacancy).filter(Vacancy.status == VacancyStatus.PENDING_APPROVAL).order_by(Vacancy.updated_at.asc()).all()

def _score_all(db: Session, vacancy: Vacancy) -> int:
    db.query(CandidateSuggestion).filter(CandidateSuggestion.vacancy_id == vacancy.id).delete()
    db.flush()
    candidates = db.query(Candidate).all()
    for c in candidates:
        result = calculate_score(c, vacancy)
        # Auto-rejeita se score abaixo do threshold
        if result.score < SCORE_THRESHOLD:
            status = SuggestionStatus.REJECTED
            reason = f"Score abaixo do mínimo de {SCORE_THRESHOLD:.0f}% (score obtido: {result.score:.1f}%)"
        else:
            status = SuggestionStatus.ACTIVE
            reason = None
        db.add(CandidateSuggestion(
            vacancy_id=vacancy.id,
            candidate_id=c.id,
            score=result.score,
            explanation_json=result.to_explanation_json(),
            status=status,
            rejection_reason=reason,
            rejected_at=datetime.utcnow() if status == SuggestionStatus.REJECTED else None,
        ))
    return len(candidates)

def approve_vacancy(db: Session, vacancy_id: int, rh_user_id: int, justification) -> ApprovalDecision:
    vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if not vacancy: raise HTTPException(status_code=404, detail="Vaga não encontrada")
    if vacancy.status != VacancyStatus.PENDING_APPROVAL: raise HTTPException(status_code=400, detail="Vaga não está aguardando aprovação")
    decision = ApprovalDecision(vacancy_id=vacancy_id, rh_user_id=rh_user_id,
                                decision=DecisionEnum.APPROVED, justification=justification, decided_at=datetime.utcnow())
    vacancy.status = VacancyStatus.APPROVED
    vacancy.updated_at = datetime.utcnow()
    db.add(decision)
    total = _score_all(db, vacancy)
    _audit(db, rh_user_id, "VACANCY_APPROVED", vacancy_id, {"candidates_scored": total})
    db.commit(); db.refresh(decision)
    return decision

def reject_vacancy(db: Session, vacancy_id: int, rh_user_id: int, justification: str) -> ApprovalDecision:
    if not justification or not justification.strip(): raise HTTPException(status_code=400, detail="Justificativa obrigatória")
    vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if not vacancy: raise HTTPException(status_code=404, detail="Vaga não encontrada")
    if vacancy.status != VacancyStatus.PENDING_APPROVAL: raise HTTPException(status_code=400, detail="Vaga não está aguardando aprovação")
    decision = ApprovalDecision(vacancy_id=vacancy_id, rh_user_id=rh_user_id,
                                decision=DecisionEnum.REJECTED, justification=justification, decided_at=datetime.utcnow())
    vacancy.status = VacancyStatus.REJECTED
    vacancy.updated_at = datetime.utcnow()
    db.add(decision)
    _audit(db, rh_user_id, "VACANCY_REJECTED", vacancy_id, {"reason": justification})
    db.commit(); db.refresh(decision)
    return decision

def rescore_vacancy(db: Session, vacancy_id: int, user_id: int) -> dict:
    vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if not vacancy: raise HTTPException(status_code=404, detail="Vaga não encontrada")
    if vacancy.status != VacancyStatus.APPROVED: raise HTTPException(status_code=400, detail="Só vagas APPROVED podem ser rescored")
    total = _score_all(db, vacancy)
    _audit(db, user_id, "VACANCY_RESCORED", vacancy_id, {"candidates_scored": total})
    db.commit()
    return {"candidates_scored": total}
