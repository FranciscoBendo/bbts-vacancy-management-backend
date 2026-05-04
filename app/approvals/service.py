from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models import Vacancy, Candidate, CandidateSuggestion, ApprovalDecision, AuditEvent, VacancyStatus, DecisionEnum
from app.scoring.engine import calculate_score

def _audit(db, actor_id, action, vacancy_id, metadata=None):
    db.add(AuditEvent(actor_user_id=actor_id, action=action, entity_type="Vacancy", entity_id=vacancy_id, metadata_json=metadata or {}))

def list_pending(db: Session) -> list[Vacancy]:
    return db.query(Vacancy).filter(Vacancy.status == VacancyStatus.PENDING_APPROVAL).order_by(Vacancy.updated_at.asc()).all()

def _score_all(db: Session, vacancy: Vacancy) -> int:
    db.query(CandidateSuggestion).filter(CandidateSuggestion.vacancy_id == vacancy.id).delete()
    db.flush()
    candidates = db.query(Candidate).all()
    for c in candidates:
        result = calculate_score(c, vacancy)
        db.add(CandidateSuggestion(vacancy_id=vacancy.id, candidate_id=c.id, score=result.score, explanation_json=result.to_explanation_json()))
    return len(candidates)

def approve_vacancy(db: Session, vacancy_id: int, rh_user_id: int, justification) -> ApprovalDecision:
    vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if not vacancy: raise HTTPException(status_code=404, detail="Vaga não encontrada")
    if vacancy.status != VacancyStatus.PENDING_APPROVAL: raise HTTPException(status_code=400, detail="Vaga não está aguardando aprovação")
    decision = ApprovalDecision(vacancy_id=vacancy_id, rh_user_id=rh_user_id, decision=DecisionEnum.APPROVED, justification=justification, decided_at=datetime.utcnow())
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
    decision = ApprovalDecision(vacancy_id=vacancy_id, rh_user_id=rh_user_id, decision=DecisionEnum.REJECTED, justification=justification, decided_at=datetime.utcnow())
    vacancy.status = VacancyStatus.REJECTED
    vacancy.updated_at = datetime.utcnow()
    db.add(decision)
    _audit(db, rh_user_id, "VACANCY_REJECTED", vacancy_id, {"reason": justification})
    db.commit(); db.refresh(decision)
    return decision

# approvals/service.py — ADICIONAR ao final do arquivo

def rescore_vacancy(vacancy_id: int, db: Session) -> int:
    """
    Recalcula o ranking de candidatos de uma vaga já aprovada.
    Apaga TODAS as sugestões antigas antes de recriar — evita duplicatas
    como as visíveis na tela (mesmo candidato aparecendo múltiplas vezes).
    Retorna o número de candidatos processados.
    """
    from app.scoring.engine import calculate_score
    from app.models import Candidate, CandidateSuggestion

    vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if not vacancy:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")

    if vacancy.status != VacancyStatus.APPROVED:
        raise HTTPException(
            status_code=400,
            detail="Rescore só pode ser executado em vagas com status APPROVED"
        )

    # ── PASSO CRÍTICO: apaga sugestões antigas ANTES de recriar ───────────────
    # Sem este delete, cada chamada ao rescore acumula novas linhas na tabela
    # candidate_suggestions sem remover as anteriores — causando as duplicatas
    # visíveis na tela (posições 3/7, 4/8, 5/9 com o mesmo candidato).
    # ──────────────────────────────────────────────────────────────────────────
    db.query(CandidateSuggestion).filter(
        CandidateSuggestion.vacancy_id == vacancy_id
    ).delete()
    db.flush()

    candidates = db.query(Candidate).all()
    for candidate in candidates:
        result = calculate_score(candidate, vacancy)
        db.add(CandidateSuggestion(
            vacancy_id=vacancy.id,
            candidate_id=candidate.id,
            score=result.score,
            explanation_json=result.to_explanation_json(),
        ))

    db.commit()
    return len(candidates)