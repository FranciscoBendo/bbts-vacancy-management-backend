from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import User, Candidate
from app.auth.service import require_rh
from app.imports import service
from app.imports.pdf_extractor import extract_from_pdf
from app.imports.schemas import IntegrationLogOut, CandidateIn
from app.candidates.schemas import CandidateDetailOut

router = APIRouter(prefix="/candidates", tags=["Import (RH)"])

@router.post("/import/pdf", response_model=CandidateDetailOut, status_code=201,
             summary="Importar candidato via PDF (Google Gemini)")
async def import_pdf(file: UploadFile = File(...), db: Session = Depends(get_db), rh: User = Depends(require_rh)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .pdf")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="PDF muito grande. Máximo: 10MB")
    try:
        extracted = await extract_from_pdf(content)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Falha na extração: {str(e)}")
    try:
        candidate, _ = service.import_from_pdf_data(db, extracted, filename=file.filename)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Falha ao salvar: {str(e)}")
    c = db.query(Candidate).options(
        joinedload(Candidate.skills), joinedload(Candidate.experiences),
        joinedload(Candidate.educations), joinedload(Candidate.languages),
        joinedload(Candidate.certifications),
    ).filter(Candidate.id == candidate.id).first()
    return CandidateDetailOut.model_validate(c)

@router.post("/import/json", response_model=IntegrationLogOut, status_code=201, summary="Importar via JSON")
def import_json(records: list[dict], db: Session = Depends(get_db), rh: User = Depends(require_rh)):
    if not records: raise HTTPException(status_code=400, detail="Lista vazia")
    return service.import_from_json(db, records)

@router.post("/import/csv", response_model=IntegrationLogOut, status_code=201, summary="Importar via CSV")
async def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db), rh: User = Depends(require_rh)):
    if not file.filename.endswith(".csv"): raise HTTPException(status_code=400, detail="Arquivo deve ser .csv")
    return service.import_from_csv(db, await file.read(), filename=file.filename)

@router.get("/import/template", summary="Baixar template CSV")
def download_template(rh: User = Depends(require_rh)):
    template = "full_name,headline,email,location,linkedin_url,skills,languages,certifications,education,experiences\nJoão Silva,Dev Backend,joao@email.com,São Paulo SP,,Python:Avançado:5;FastAPI:Inter:2,Inglês:B2,AWS:Amazon:2023,USP:CC:Bach:2018,BBTS:Dev:2022:2024:false\n"
    return PlainTextResponse(content=template, headers={"Content-Disposition": "attachment; filename=candidatos_template.csv"}, media_type="text/csv")
