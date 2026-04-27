"""
imports/pdf_extractor.py — Sprint 3 (Groq)
───────────────────────────────────────────
Fluxo:
  1. pypdf extrai o texto do PDF
  2. Groq (LLaMA 3.3 70B) analisa o texto e retorna JSON estruturado
  3. Fallback: se Groq falhar, extrai skills por palavras-chave do texto

Modelo: llama-3.3-70b-versatile (gratuito no tier free do Groq)
Limite free: 14.400 requisições/dia · 6.000 tokens/min
"""
import json
import re
import io
import httpx
import pypdf
from app.config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """Você é um sistema especializado em extração de dados de currículos profissionais.
Analise o texto fornecido e extraia as informações em formato JSON estruturado.
Retorne APENAS o JSON válido, sem markdown, sem ```json, sem explicações."""

USER_PROMPT_TEMPLATE = """Extraia os dados do currículo abaixo e retorne SOMENTE este JSON preenchido:

{{
  "full_name": "Nome completo do candidato",
  "headline": "Título profissional ou cargo mais recente (máximo 100 caracteres)",
  "email": "email@exemplo.com ou null",
  "location": "Cidade, Estado ou null",
  "linkedin_url": "URL do LinkedIn ou null",
  "skills": [
    {{"name": "nome da skill", "level": "Básico|Intermediário|Avançado ou null", "years_experience": número ou null}}
  ],
  "languages": [
    {{"name": "Idioma", "level": "Básico|Intermediário|Avançado|Fluente ou null"}}
  ],
  "certifications": [
    {{"name": "Nome da certificação", "issuer": "Emissor ou null", "year": ano_número ou null}}
  ],
  "educations": [
    {{"institution": "Nome da instituição", "course": "Nome do curso", "degree": "Bacharelado|Mestrado|Doutorado|Tecnólogo|MBA ou null", "graduation_year": ano_número ou null}}
  ],
  "experiences": [
    {{"company": "Nome da empresa", "role": "Cargo", "start_year": ano_número ou null, "end_year": ano_número ou null, "current": true ou false}}
  ]
}}

Regras importantes:
- skills: extraia TODAS as tecnologias, ferramentas e competências mencionadas
- experiences: ordene do mais recente para o mais antigo
- current: true apenas no emprego atual
- Se um campo não existir no currículo, use null
- years_experience: estime baseado no tempo de uso ou tempo nas experiências

Texto do currículo:
{text}"""


def _extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extrai texto puro do PDF usando pypdf."""
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    text = ""
    for page in reader.pages:
        text += (page.extract_text() or "") + "\n"
    return text.strip()


async def _extract_with_groq(text: str) -> dict:
    """Envia o texto para o Groq e retorna o JSON extraído."""
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY não configurada no .env")

    # Limita o texto para não exceder tokens (Groq free: ~6k tokens/min)
    text_truncated = text[:8000] if len(text) > 8000 else text

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(text=text_truncated)},
        ],
        "temperature": 0.1,
        "max_tokens": 2048,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            GROQ_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
        )

    if r.status_code != 200:
        raise ValueError(f"Groq API error {r.status_code}: {r.text}")

    try:
        content = r.json()["choices"][0]["message"]["content"].strip()
        # Remove possíveis marcadores markdown
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content.strip())
    except Exception as e:
        raise ValueError(f"Falha ao parsear resposta do Groq: {e}")


def _extract_fallback(text: str, filename: str = "") -> dict:
    """
    Fallback quando a IA não está disponível.
    Extrai nome, email, LinkedIn e skills por palavras-chave do texto.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    full_name = lines[0] if lines else filename.replace(".pdf", "").replace("_", " ").replace("-", " ").title()
    headline = lines[1] if len(lines) > 1 else "Perfil importado via PDF"
    if len(headline) > 100:
        headline = headline[:100]

    email = None
    email_match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    if email_match:
        email = email_match.group(0)

    linkedin = None
    li_match = re.search(r"linkedin\.com/in/[\w\-]+", text, re.IGNORECASE)
    if li_match:
        linkedin = "https://" + li_match.group(0)

    KNOWN_SKILLS = [
        "python", "java", "javascript", "typescript", "react", "node.js", "nodejs",
        "spring boot", "fastapi", "django", "flask", "sql", "postgresql", "mysql",
        "mongodb", "docker", "kubernetes", "aws", "azure", "gcp", "git", "linux",
        "apache spark", "kafka", "redis", "elasticsearch", "c#", "c++", "golang",
        "php", "ruby", "swift", "kotlin", "flutter", "angular", "vue", "next.js",
        "machine learning", "deep learning", "nlp", "pandas", "numpy", "tensorflow",
        "pytorch", "dbt", "airflow", "power bi", "tableau", "excel",
    ]
    text_lower = text.lower()
    found_skills = [
        {"name": s, "level": None, "years_experience": None}
        for s in KNOWN_SKILLS if s in text_lower
    ]

    return {
        "full_name": full_name,
        "headline": headline,
        "email": email,
        "location": "",
        "linkedin_url": linkedin,
        "skills": found_skills,
        "languages": [],
        "certifications": [],
        "educations": [],
        "experiences": [],
    }


async def extract_from_pdf(pdf_bytes: bytes, filename: str = "curriculo.pdf") -> dict:
    """
    Pipeline completo de extração:
    1. Extrai texto do PDF via pypdf
    2. Tenta análise via Groq (LLaMA 3.3 70B)
    3. Se falhar, usa extração por palavras-chave como fallback
    """
    # Extrai texto do PDF
    try:
        text = _extract_text_from_pdf(pdf_bytes)
    except Exception as e:
        print(f"[pdf_extractor] Erro ao ler PDF: {e}")
        text = ""

    if not text.strip():
        print("[pdf_extractor] PDF sem texto extraível. Usando fallback mínimo.")
        return _extract_fallback("", filename)

    # Tenta Groq
    if settings.GROQ_API_KEY:
        try:
            result = await _extract_with_groq(text)
            # Garante que location nunca seja None (evita erro de validação)
            if result.get("location") is None:
                result["location"] = ""
            print(f"[pdf_extractor] Extração Groq bem-sucedida: {result.get('full_name')}")
            return result
        except Exception as e:
            print(f"[pdf_extractor] Groq falhou: {e}. Usando fallback de palavras-chave.")

    # Fallback por palavras-chave
    print("[pdf_extractor] Usando fallback de extração por palavras-chave.")
    return _extract_fallback(text, filename)
