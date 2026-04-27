from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import User, Candidate
from app.auth.service import require_rh
from app.imports import service
from app.imports.pdf_extractor import extract_from_pdf
from app.imports.schemas import IntegrationLogOut
from app.candidates.schemas import CandidateDetailOut

router = APIRouter(prefix="/candidates", tags=["Import (RH)"])


@router.post("/import/pdf", response_model=CandidateDetailOut, status_code=201,
             summary="Importar candidato via PDF (Groq — LLaMA 3.3 70B)")
async def import_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    rh: User = Depends(require_rh),
):
    """
    Envia um PDF de currículo para análise pelo **Groq (LLaMA 3.3 70B)**.

    O sistema extrai automaticamente:
    - Dados pessoais (nome, email, localização, LinkedIn)
    - Skills com nível e anos de experiência
    - Experiências profissionais
    - Formação acadêmica
    - Idiomas e certificações

    Se a IA estiver indisponível, extrai skills por palavras-chave automaticamente.
    Sinônimos são normalizados (ex: "JS" → "javascript").
    Se o candidato já existir pelo e-mail, seus dados são **atualizados**.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .pdf")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="PDF muito grande. Máximo: 10MB")

    extracted = await extract_from_pdf(content, filename=file.filename)

    try:
        candidate, _ = service.import_from_pdf_data(db, extracted, filename=file.filename)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Falha ao salvar candidato: {str(e)}")

    c = db.query(Candidate).options(
        joinedload(Candidate.skills),
        joinedload(Candidate.experiences),
        joinedload(Candidate.educations),
        joinedload(Candidate.languages),
        joinedload(Candidate.certifications),
    ).filter(Candidate.id == candidate.id).first()
    return CandidateDetailOut.model_validate(c)


@router.post("/import/json", response_model=IntegrationLogOut, status_code=201,
             summary="Importar candidatos via JSON")
def import_json(records: list[dict], db: Session = Depends(get_db), rh: User = Depends(require_rh)):
    if not records:
        raise HTTPException(status_code=400, detail="Lista vazia")
    return service.import_from_json(db, records)


@router.post("/import/csv", response_model=IntegrationLogOut, status_code=201,
             summary="Importar candidatos via CSV")
async def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    rh: User = Depends(require_rh),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .csv")
    return service.import_from_csv(db, await file.read(), filename=file.filename)


@router.get("/import/template", summary="Baixar template CSV")
def download_template(rh: User = Depends(require_rh)):
    template = (
        "full_name,headline,email,location,linkedin_url,skills,languages,certifications,education,experiences\n"
        "João Silva,Dev Backend,joao@email.com,São Paulo SP,,Python:Avançado:5;FastAPI:Inter:2,Inglês:B2,AWS:Amazon:2023,USP:CC:Bach:2018,BBTS:Dev:2022:2024:false\n"
    )
    return PlainTextResponse(
        content=template,
        headers={"Content-Disposition": "attachment; filename=candidatos_template.csv"},
        media_type="text/csv",
    )
