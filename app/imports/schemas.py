from typing import Optional
# ── MODIFICAÇÃO 1 ──────────────────────────────────────────────────────────────
# Adicionado 'field_validator' ao import do pydantic.
# Ele permite interceptar e transformar valores ANTES da validação de tipo,
# o que nos dá a chance de converter None → "" em vez de lançar ValidationError.
from pydantic import BaseModel, field_validator

class SkillIn(BaseModel):
    name: str
    level: Optional[str] = None
    years_experience: Optional[float] = None

# ── MODIFICAÇÃO 2 ──────────────────────────────────────────────────────────────
# Alterados os tipos de 'company' e 'role' de 'str' para 'Optional[str]'.
#
# ANTES:  company: str
#         role: str
#
# DEPOIS: company: Optional[str] = None
#         role: Optional[str] = None
#
# Por quê: o Groq (LLaMA 3.3 70B) às vezes retorna null nesses campos quando
# não consegue identificar a empresa ou o cargo no PDF. Com o tipo 'str' puro,
# o Pydantic lança ValidationError imediatamente ao receber None, gerando o
# HTTP 422. Ao aceitar Optional[str], o valor None consegue entrar no validator
# abaixo, que então o converte para string vazia antes de qualquer erro.
# ──────────────────────────────────────────────────────────────────────────────
class ExperienceIn(BaseModel):
    company: Optional[str] = None   # era: company: str
    role: Optional[str] = None      # era: role: str
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    current: bool = False
    # ── MODIFICAÇÃO 3 ────────────────────────────────────────────────────────
    # Adicionado field_validator para 'company' e 'role'.
    #
    # mode="before" significa que esta função roda ANTES da validação de tipo
    # do Pydantic — ou seja, recebemos o valor cru vindo do JSON (que pode ser
    # None, int, etc.) e devolvemos algo seguro antes que o Pydantic tente
    # encaixá-lo no tipo declarado.
    #
    # Lógica: se 'v' já é uma string válida, mantém como está.
    #         Se for None (ou qualquer outro tipo inesperado), retorna "".
    #
    # Resultado: None  → ""   (evita o 422)
    #            "BBTS" → "BBTS"  (mantém valor correto intacto)
    # ─────────────────────────────────────────────────────────────────────────
    @field_validator("company", "role", mode="before")
    @classmethod
    def coerce_none_to_empty(cls, v: object) -> str:
        return v if isinstance(v, str) else ""

class EducationIn(BaseModel):
    institution: str
    course: str
    degree: Optional[str] = None
    graduation_year: Optional[int] = None

class LanguageIn(BaseModel):
    name: str
    level: Optional[str] = None

class CertificationIn(BaseModel):
    name: str
    issuer: Optional[str] = None
    year: Optional[int] = None

class CandidateIn(BaseModel):
    full_name: str
    headline: str = ""
    email: Optional[str] = None
    location: str = ""
    linkedin_url: Optional[str] = None
    skills: list[SkillIn] = []
    experiences: list[ExperienceIn] = []
    educations: list[EducationIn] = []
    languages: list[LanguageIn] = []
    certifications: list[CertificationIn] = []

class IntegrationLogOut(BaseModel):
    id: int
    source: str
    filename: Optional[str]
    status: str
    total_records: int
    success_count: int
    error_count: int
    errors_json: Optional[list] = None
    model_config = {"from_attributes": True}
