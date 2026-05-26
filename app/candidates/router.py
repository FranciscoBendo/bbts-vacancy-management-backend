from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.auth.service import get_current_user, require_rh
from app.candidates import service
from app.candidates.schemas import (
    CandidateOut, CandidateDetailOut, CandidateListOut,
    CandidateListByVacancyOut, RejectCandidateRequest
)

router = APIRouter(tags=["Candidates"])


@router.get("/vacancies/{vacancy_id}/candidates", response_model=CandidateListByVacancyOut,
            summary="Candidatos por vaga (score ≥ 40%) + recusados")
def get_candidates(vacancy_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    active, rejected, total = service.get_candidates(db, vacancy_id)
    return {
        "candidates": active,
        "rejected": rejected,
        "total_before_filter": total,
        "score_threshold": service.SCORE_THRESHOLD,
    }


@router.post("/vacancies/{vacancy_id}/candidates/{suggestion_id}/reject",
             response_model=CandidateOut, summary="Recusar candidato manualmente (RH)")
def reject_candidate(
    vacancy_id: int,
    suggestion_id: int,
    body: RejectCandidateRequest,
    db: Session = Depends(get_db),
    rh: User = Depends(require_rh),
):
    return service.reject_candidate(db, vacancy_id, suggestion_id, body.reason, rh)


@router.get("/candidates", response_model=list[CandidateListOut], summary="Listar candidatos com filtros")
def list_candidates(
    skill: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.list_candidates(db, skill=skill, location=location)


@router.get("/candidates/{candidate_id}", response_model=CandidateDetailOut, summary="Perfil completo")
def get_candidate_detail(candidate_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.get_candidate_detail(db, candidate_id)
