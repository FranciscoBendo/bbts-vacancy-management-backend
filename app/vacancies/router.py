from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.auth.service import get_current_user
from app.vacancies import service
from app.vacancies.schemas import VacancyCreate, VacancyUpdate, VacancyOut, VacancyList
# vacancies/router.py — ADICIONAR o import junto aos demais imports do arquivo
from app.approvals.service import rescore_vacancy

router = APIRouter(prefix="/vacancies", tags=["Vacancies"])


@router.get("", response_model=list[VacancyList], summary="Listar vagas")
def list_vacancies(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    REQUESTER → vê apenas suas vagas.
    RH → vê todas as vagas.
    """
    return service.list_vacancies(db, user)


@router.post("", response_model=VacancyOut, status_code=201, summary="Criar vaga")
def create_vacancy(
    body: VacancyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.create_vacancy(db, body, user.id)


@router.get("/{vacancy_id}", response_model=VacancyOut, summary="Detalhe da vaga")
def get_vacancy(
    vacancy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.get_vacancy_or_404(db, vacancy_id)


@router.patch("/{vacancy_id}", response_model=VacancyOut, summary="Editar vaga (apenas DRAFT)")
def update_vacancy(
    vacancy_id: int,
    body: VacancyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.update_vacancy(db, vacancy_id, body, user)


@router.post("/{vacancy_id}/submit", response_model=VacancyOut, summary="Submeter para aprovação")
def submit_vacancy(
    vacancy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.submit_vacancy(db, vacancy_id, user)
    
# Adicionado rescore
@router.post("/{vacancy_id}/rescore", tags=["Vacancies"])
def rescore_vacancy_endpoint(
    vacancy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Recalcula o ranking de candidatos de uma vaga aprovada.
    Pode ser chamado múltiplas vezes com segurança — cada chamada
    apaga e recria todas as sugestões sem gerar duplicatas.
    """
    total = rescore_vacancy(vacancy_id, db)
    return {"message": f"Rescore concluído. {total} candidato(s) processado(s)."}
