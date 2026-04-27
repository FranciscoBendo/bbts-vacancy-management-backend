from __future__ import annotations
from dataclasses import dataclass, field
from app.models import Candidate, Vacancy, RequirementType
from app.synonyms.dictionary import normalize_skill

MANDATORY_PENALTY = 0.30
LOCATION_PENALTY  = 0.10

def _norm(text: str) -> str:
    return normalize_skill(text.lower().strip())

def _matches(req_name: str, values: list[str]) -> bool:
    req = _norm(req_name)
    return any(req in _norm(v) or _norm(v) in req for v in values)

def _location_matches(candidate_loc: str, vacancy_loc: str) -> bool:
    if not candidate_loc or not vacancy_loc: return True
    c = candidate_loc.lower().strip()
    v = vacancy_loc.lower().strip()
    for term in ["(híbrido)","(presencial)","(remoto)","híbrido","presencial","remoto"]:
        v = v.replace(term, "").strip()
    c_city = c.split(",")[0].strip()
    v_city = v.split(",")[0].strip()
    return c_city in v or v_city in c or c in v

@dataclass
class ScoreResult:
    score: float
    met_requirements: int
    total_requirements: int
    missing_mandatory: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    location_match: bool = True

    def to_explanation_json(self) -> dict:
        return {
            "met_requirements": self.met_requirements,
            "total_requirements": self.total_requirements,
            "missing_mandatory": self.missing_mandatory,
            "strengths": self.strengths,
            "location_match": self.location_match,
        }

def calculate_score(candidate: Candidate, vacancy: Vacancy) -> ScoreResult:
    requirements = vacancy.requirements
    if not requirements:
        return ScoreResult(score=0.0, met_requirements=0, total_requirements=0)

    total_weight = sum(r.weight for r in requirements)
    earned_weight = 0.0
    met = 0
    missing_mandatory: list[str] = []
    strengths: list[str] = []

    for req in requirements:
        matched = False
        if req.type == RequirementType.SKILL:
            matched = _matches(req.name, [s.name for s in candidate.skills])
        elif req.type == RequirementType.LANGUAGE:
            matched = _matches(req.name, [l.name for l in candidate.languages])
        elif req.type == RequirementType.CERTIFICATION:
            matched = _matches(req.name, [c.name for c in candidate.certifications])
        elif req.type == RequirementType.EDUCATION:
            matched = _matches(req.name, [e.course for e in candidate.educations] + [e.institution for e in candidate.educations])
        elif req.type == RequirementType.COMPANY:
            matched = _matches(req.name, [ex.company for ex in candidate.experiences])
        elif req.type == RequirementType.LOCATION:
            matched = _location_matches(candidate.location or "", req.name)

        if matched:
            earned_weight += req.weight; met += 1
            skill = next((s for s in candidate.skills if _norm(req.name) in _norm(s.name) or _norm(s.name) in _norm(req.name)), None)
            detail = req.name
            if skill and skill.years_experience: detail += f" ({skill.years_experience:.0f} anos)"
            strengths.append(detail)
        elif req.mandatory:
            missing_mandatory.append(req.name)

    base = (earned_weight / total_weight) * 100 if total_weight > 0 else 0.0
    score = base * max(0.0, 1.0 - len(missing_mandatory) * MANDATORY_PENALTY)
    loc_match = _location_matches(candidate.location or "", vacancy.location)
    if not loc_match: score *= (1.0 - LOCATION_PENALTY)

    return ScoreResult(
        score=round(min(100.0, max(0.0, score)), 1),
        met_requirements=met, total_requirements=len(requirements),
        missing_mandatory=missing_mandatory, strengths=strengths, location_match=loc_match,
    )
