from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Vacancy, VacancyStatus
from app.auth.service import get_current_user
from app.connectors.external import fetch_external_candidates
from app.imports.schemas import CandidateIn
from app.imports.service import _upsert
from app.approvals.service import _score_all

router = APIRouter(prefix="/vacancies", tags=["Conectores Externos"])


@router.post("/{vacancy_id}/import-external", summary="Buscar candidatos externos (randomuser.me)")
async def import_external(
    vacancy_id: int,
    count: int = Query(default=10, ge=1, le=30, description="Número de candidatos a buscar"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Busca candidatos externos via API pública (randomuser.me),
    enriquece com skills baseadas nos requisitos da vaga,
    importa para o banco e recalcula o ranking automaticamente.
    """
    vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if not vacancy:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    if vacancy.status != VacancyStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Só vagas APPROVED podem receber candidatos externos")

    try:
        raw_candidates = await fetch_external_candidates(vacancy, count=count)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao buscar candidatos externos: {str(e)}")

    imported = 0
    skipped = 0
    for raw in raw_candidates:
        try:
            _upsert(db, CandidateIn(**raw))
            imported += 1
        except Exception:
            skipped += 1

    # Recalcula ranking com os novos candidatos
    _score_all(db, vacancy)
    db.commit()

    return {
        "imported": imported,
        "skipped": skipped,
        "message": f"{imported} candidato(s) importado(s) e ranking recalculado.",
    }