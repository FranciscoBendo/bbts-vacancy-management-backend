from typing import Optional
from sqlalchemy import or_
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from app.models import CandidateSuggestion, Candidate, Vacancy, CandidateSkill, IntegrationLog, IntegrationStatus
from app.candidates.schemas import CandidateOut, CandidateExplanation, CandidateDetailOut
from app.synonyms.dictionary import normalize_skill
from app.imports.service import _upsert
from app.imports.schemas import CandidateIn

# ── MODIFICAÇÃO 1 ──────────────────────────────────────────────────────────────
# Definida como constante para facilitar ajuste futuro sem precisar alterar
# múltiplos pontos do código. Se o time decidir mudar o limiar de 30% para
# outro valor, basta alterar aqui.
# ──────────────────────────────────────────────────────────────────────────────
SCORE_THRESHOLD = 30.0


def get_candidates(db: Session, vacancy_id: int) -> tuple[list[CandidateOut], int]:
    if not db.query(Vacancy).filter(Vacancy.id == vacancy_id).first():
        raise HTTPException(status_code=404, detail="Vaga não encontrada")

    # ── MODIFICAÇÃO 2 ──────────────────────────────────────────────────────────
    # Conta o total de candidatos da vaga ANTES de aplicar o filtro de score.
    # Esse valor é retornado junto com a lista para que o frontend consiga
    # distinguir dois casos:
    #   - total_before_filter > 0 e lista vazia → candidatos existem mas nenhum
    #     alcança o mínimo → exibe "Nenhum candidato alcança o mínimo de 30%"
    #   - total_before_filter == 0 e lista vazia → vaga sem candidatos
    #     → exibe "Nenhum candidato encontrado para esta vaga"
    # ──────────────────────────────────────────────────────────────────────────
    total_before_filter = (
        db.query(CandidateSuggestion)
        .filter(CandidateSuggestion.vacancy_id == vacancy_id)
        .count()
    )

    # ── MODIFICAÇÃO 3 ──────────────────────────────────────────────────────────
    # Adicionado filtro score >= SCORE_THRESHOLD à query principal.
    # Candidatos abaixo do limiar não são retornados, reduzindo o payload
    # e evitando que candidatos pouco relevantes apareçam no ranking.
    # ──────────────────────────────────────────────────────────────────────────
    suggestions = (
        db.query(CandidateSuggestion)
        .options(joinedload(CandidateSuggestion.candidate))
        .filter(CandidateSuggestion.vacancy_id == vacancy_id)
        .filter(CandidateSuggestion.score >= SCORE_THRESHOLD)  # ← filtro de score mínimo
        .order_by(CandidateSuggestion.score.desc())
        .all()
    )

    candidates = [
        CandidateOut(
            id=s.id,
            vacancy_id=s.vacancy_id,
            candidate_id=s.candidate_id,
            full_name=s.candidate.full_name,
            headline=s.candidate.headline,
            location=s.candidate.location,
            score=s.score,
            explanation=CandidateExplanation(**s.explanation_json),
        )
        for s in suggestions
    ]

    # ── MODIFICAÇÃO 4 ──────────────────────────────────────────────────────────
    # Função agora retorna uma tupla (candidates, total_before_filter) em vez
    # de apenas a lista. O router deve ser atualizado para desempacotar a tupla
    # e incluir total_before_filter e score_threshold na resposta.
    # ──────────────────────────────────────────────────────────────────────────
    return candidates, total_before_filter


def get_candidate_detail(db: Session, candidate_id: int) -> CandidateDetailOut:
    c = db.query(Candidate).options(joinedload(Candidate.skills), joinedload(Candidate.experiences), joinedload(Candidate.educations), joinedload(Candidate.languages), joinedload(Candidate.certifications)).filter(Candidate.id == candidate_id).first()
    if not c: raise HTTPException(status_code=404, detail="Candidato não encontrado")
    return CandidateDetailOut.model_validate(c)


def list_candidates(
    db: Session,
    skill: Optional[str] = None,
    location: Optional[str] = None,
) -> list:
    q = db.query(Candidate).options(joinedload(Candidate.skills))
    if location:
        q = q.filter(Candidate.location.ilike(f"%{location}%"))
    if skill:
        normalized = normalize_skill(skill)
        q = q.filter(
            Candidate.skills.any(
                or_(
                    CandidateSkill.name.ilike(f"%{skill}%"),
                    CandidateSkill.name.ilike(f"%{normalized}%"),
                )
            )
        )
    result = []
    for c in q.order_by(Candidate.created_at.desc()).all():
        result.append({
            "id": c.id,
            "full_name": c.full_name,
            "headline": c.headline,
            "location": c.location,
            "email": c.email,
            "skills_summary": [s.name for s in c.skills[:5]],
            "created_at": c.created_at,
        })
    return result


def import_from_pdf_data(db: Session, extracted: dict, filename: str) -> tuple:
    """Recebe dados extraídos pelo Groq, normaliza, persiste e gera log."""
    try:
        candidate = _upsert(db, CandidateIn(**extracted))
        log = IntegrationLog(
            source="PDF",
            filename=filename,
            status=IntegrationStatus.SUCCESS,
            total_records=1,
            success_count=1,
            error_count=0,
        )
        db.add(log)
        db.commit()
        db.refresh(candidate)
        db.refresh(log)
        return candidate, log
    except Exception as e:
        db.rollback()
        log = IntegrationLog(
            source="PDF",
            filename=filename,
            status=IntegrationStatus.FAILED,
            total_records=1,
            success_count=0,
            error_count=1,
            errors_json=[{"row": 1, "message": str(e)}],
        )
        db.add(log)
        db.commit()
        raise

# DEPOIS — retorna tupla (lista_filtrada, total_sem_filtro)
def list_candidates_by_vacancy(db: Session, vacancy_id: int) -> tuple:
    # Conta todos os candidatos da vaga, sem filtro de score
    total_before_filter = (
        db.query(CandidateSuggestion)
        .filter(CandidateSuggestion.vacancy_id == vacancy_id)
        .count()
    )

    # Busca apenas os candidatos acima do score mínimo
    candidates = (
        db.query(CandidateSuggestion)
        .filter(CandidateSuggestion.vacancy_id == vacancy_id)
        .filter(CandidateSuggestion.score >= 30)
        .order_by(CandidateSuggestion.score.desc())
        .all()
    )

    return candidates, total_before_filter