from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.auth.service import get_current_user
from app.candidates import service
from app.candidates.schemas import CandidateOut, CandidateDetailOut, CandidateListOut

# ── MODIFICAÇÃO 1 ──────────────────────────────────────────────────────────────
# Adicionado import de CandidateListByVacancyOut — novo schema que encapsula
# a lista de candidatos filtrada junto com os metadados de filtragem
# (total_before_filter e score_threshold), necessários para o frontend
# distinguir "vaga sem candidatos" de "nenhum candidato alcança o mínimo".
# ──────────────────────────────────────────────────────────────────────────────
from app.candidates.schemas import CandidateListByVacancyOut

router = APIRouter(tags=["Candidates"])


# ── MODIFICAÇÃO 2 ──────────────────────────────────────────────────────────────
# Endpoint atualizado em três pontos:
#
# 1. response_model alterado de list[CandidateOut] para CandidateListByVacancyOut
#    — o contrato da resposta agora inclui os campos candidates, total_before_filter
#    e score_threshold além da lista de candidatos.
#
# 2. service.get_candidates() agora retorna uma tupla (candidates, total_before_filter)
#    em vez de uma lista direta — desempacotada nas variáveis abaixo.
#
# 3. Retorno alterado de `return candidates` para um dict estruturado com todos
#    os campos esperados pelo CandidateListByVacancyOut.
# ──────────────────────────────────────────────────────────────────────────────
@router.get(
    "/vacancies/{vacancy_id}/candidates",
    response_model=CandidateListByVacancyOut,          # era: response_model=list[CandidateOut]
    summary="Candidatos por vaga (score desc)",
)
def get_candidates(
    vacancy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Desempacota a tupla retornada pelo service após a Modificação 4 de service.py
    candidates, total_before_filter = service.get_candidates(db, vacancy_id)  # era: return service.get_candidates(db, vacancy_id)

    return {
        "candidates": candidates,
        "total_before_filter": total_before_filter,
        "score_threshold": service.SCORE_THRESHOLD,    # usa a constante definida no service
    }


@router.get("/candidates", response_model=list[CandidateListOut], summary="Listar candidatos com filtros")
def list_candidates(
    skill: Optional[str] = Query(None, description="Filtrar por skill (ex: python)"),
    location: Optional[str] = Query(None, description="Filtrar por localização"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.list_candidates(db, skill=skill, location=location)


@router.get("/candidates/{candidate_id}", response_model=CandidateDetailOut, summary="Perfil completo do candidato")
def get_candidate_detail(
    candidate_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.get_candidate_detail(db, candidate_id)