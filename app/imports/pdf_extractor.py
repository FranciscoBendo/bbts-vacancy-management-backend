"""
imports/pdf_extractor.py
Usa Google Gemini 2.0 Flash para extrair dados estruturados de currículos PDF.
Fallback: quando Gemini indisponível, extrai texto básico do PDF via pypdf.
"""
import json
import base64
import re
import httpx
from app.config import settings

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

PROMPT = """
Você é um sistema de extração de dados de currículos profissionais.
Analise o PDF e extraia as informações no JSON abaixo.
Retorne APENAS o JSON, sem markdown, sem ```json, sem texto extra.

{
  "full_name": "Nome completo",
  "headline": "Título profissional ou cargo mais recente (max 100 chars)",
  "email": "email@exemplo.com ou null",
  "location": "Cidade, Estado ou null",
  "linkedin_url": "URL ou null",
  "skills": [{"name": "skill", "level": "Básico|Intermediário|Avançado ou null", "years_experience": número ou null}],
  "languages": [{"name": "Idioma", "level": "nível ou null"}],
  "certifications": [{"name": "nome", "issuer": "emissor ou null", "year": ano ou null}],
  "educations": [{"institution": "instituição", "course": "curso", "degree": "grau ou null", "graduation_year": ano ou null}],
  "experiences": [{"company": "empresa", "role": "cargo", "start_year": ano ou null, "end_year": ano ou null, "current": true/false}]
}

Regras:
- skills: extraia TODAS as tecnologias e competências mencionadas
- experiences: ordene do mais recente para o mais antigo
- current: true apenas no emprego atual
- Se não existir no currículo, use null
"""


async def extract_from_pdf(pdf_bytes: bytes) -> dict:
    """
    Tenta extrair via Gemini. Se falhar (quota, rede, etc),
    cai no fallback de extração por texto.
    """
    if settings.GEMINI_API_KEY:
        try:
            return await _extract_with_gemini(pdf_bytes)
        except Exception as e:
            print(f"[pdf_extractor] Gemini falhou: {e}. Usando fallback de texto.")

    return _extract_fallback(pdf_bytes)


async def _extract_with_gemini(pdf_bytes: bytes) -> dict:
    payload = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": "application/pdf", "data": base64.b64encode(pdf_bytes).decode()}},
            {"text": PROMPT},
        ]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4096},
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(f"{GEMINI_URL}?key={settings.GEMINI_API_KEY}", json=payload)

    if r.status_code != 200:
        raise ValueError(f"Gemini API error {r.status_code}: {r.text}")

    try:
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        raise ValueError(f"Falha ao parsear resposta do Gemini: {e}")


def _extract_fallback(pdf_bytes: bytes) -> dict:
    """
    Extração básica por texto puro do PDF.
    Usa pypdf se disponível, senão retorna estrutura mínima.
    """
    text = ""
    try:
        import pypdf
        import io
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception:
        pass

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Tenta extrair nome (primeira linha não vazia)
    full_name = lines[0] if lines else "Candidato Importado"

    # Tenta extrair email
    email = None
    email_match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    if email_match:
        email = email_match.group(0)

    # Tenta extrair LinkedIn
    linkedin = None
    li_match = re.search(r"linkedin\.com/in/[\w\-]+", text, re.IGNORECASE)
    if li_match:
        linkedin = "https://" + li_match.group(0)

    # Headline: segunda linha não vazia
    headline = lines[1] if len(lines) > 1 else "Perfil importado via PDF"
    if len(headline) > 100:
        headline = headline[:100]

    # Skills: palavras-chave técnicas conhecidas encontradas no texto
    KNOWN_SKILLS = [
        "python","java","javascript","typescript","react","node","spring","fastapi",
        "django","flask","sql","postgresql","mysql","mongodb","docker","kubernetes",
        "aws","azure","gcp","git","linux","spark","kafka","redis","elasticsearch",
        "c#","c++","golang","php","ruby","swift","kotlin","flutter","angular","vue",
        "machine learning","deep learning","nlp","pandas","numpy","tensorflow","pytorch",
        "dbt","airflow","power bi","tableau","excel","scrum","agile",
    ]
    text_lower = text.lower()
    found_skills = [{"name": s, "level": None, "years_experience": None}
                    for s in KNOWN_SKILLS if s in text_lower]

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