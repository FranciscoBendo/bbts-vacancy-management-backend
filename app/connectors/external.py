"""
connectors/external.py
Conector com randomuser.me — API pública gratuita.
Gera candidatos externos realistas baseados nos requisitos da vaga.
"""
import random
import httpx
from app.models import Vacancy, RequirementType

RANDOMUSER_URL = "https://randomuser.me/api/"

# Skills extras para enriquecer perfis
EXTRA_SKILLS = [
    "Git", "Docker", "Linux", "SQL", "Scrum", "Agile",
    "REST API", "Microsserviços", "CI/CD", "AWS",
]

LEVELS = ["Básico", "Intermediário", "Avançado"]
LOCATIONS_BR = [
    "São Paulo, SP", "Rio de Janeiro, RJ", "Belo Horizonte, MG",
    "Curitiba, PR", "Porto Alegre, RS", "Recife, PE",
    "Salvador, BA", "Fortaleza, CE", "Campinas, SP", "Brasília, DF",
]


async def fetch_external_candidates(vacancy: Vacancy, count: int = 10) -> list[dict]:
    """
    Busca candidatos externos via randomuser.me e os enriquece
    com skills baseadas nos requisitos da vaga.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(RANDOMUSER_URL, params={
            "results": count,
            "nat": "br",
            "inc": "name,email,location",
        })
        r.raise_for_status()
        users = r.json()["results"]

    # Extrai nomes de skills dos requisitos da vaga
    vacancy_skills = [
        req.name for req in vacancy.requirements
        if req.type in (RequirementType.SKILL, RequirementType.LANGUAGE, RequirementType.CERTIFICATION)
    ]

    candidates = []
    for u in users:
        full_name = f"{u['name']['first']} {u['name']['last']}"
        email = u["email"]

        # Cada candidato atende entre 30% e 100% das skills da vaga
        num_matching = random.randint(
            max(1, int(len(vacancy_skills) * 0.3)),
            len(vacancy_skills),
        )
        chosen_skills = random.sample(vacancy_skills, min(num_matching, len(vacancy_skills)))

        # Adiciona algumas skills extras aleatórias
        extras = random.sample(EXTRA_SKILLS, random.randint(1, 3))
        all_skills = list({*chosen_skills, *extras})

        skills = [
            {
                "name": s,
                "level": random.choice(LEVELS),
                "years_experience": round(random.uniform(0.5, 10.0), 1),
            }
            for s in all_skills
        ]

        candidates.append({
            "full_name": full_name,
            "headline": f"Profissional captado via conector externo",
            "email": email,
            "location": random.choice(LOCATIONS_BR),
            "linkedin_url": None,
            "skills": skills,
            "languages": [{"name": "Inglês", "level": random.choice(LEVELS)}],
            "certifications": [],
            "educations": [],
            "experiences": [],
        })

    return candidates