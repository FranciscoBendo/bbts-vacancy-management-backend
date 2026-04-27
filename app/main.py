import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.auth.router import router as auth_router
from app.vacancies.router import router as vacancies_router
from app.approvals.router import router as approvals_router
from app.candidates.router import router as candidates_router
from app.imports.router import router as imports_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

app = FastAPI(title="BBTS — Gestão de Vagas API", version="2.0.0", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.exception_handler(Exception)
async def global_handler(request: Request, exc: Exception):
    logging.error("Unhandled: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Erro interno"})

app.include_router(auth_router)
app.include_router(vacancies_router)
app.include_router(approvals_router)
app.include_router(candidates_router)
app.include_router(imports_router)

@app.get("/health", tags=["Health"])
def health(): return {"status": "ok", "sprint": 2}
