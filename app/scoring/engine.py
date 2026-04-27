from __future__ import annotations
from dataclasses import dataclass, field
from app.models import Candidate, Vacancy, RequirementType

MANDATORY_PENALTY = 0.30

def _normalize(text: str) -> str:
    return text.lower().strip()

def _matches(req_name: str, values: list[str]) -> bool:
    req = _normalize(req_name)
    return any(req in _normalize(v) or _normalize(v) in req for v in values)

@dataclass
class ScoreResult:
    score: float
    met_requirements: int
    total_requirements: int
    missing_mandatory: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)

    def to_explanation_json(self) -> dict:
        return {
            "met_requirements": self.met_requirements,
            "total_requirements": self.total_requirements,
            "missing_mandatory": self.missing_mandatory,
            "strengths": self.strengths,
        }

def calculate_score(candidate: Candidate, vacancy: Vacancy) -> ScoreResult:
    requirements = vacancy.requirements
    if not requirements:
        return ScoreResult(score=0.0, met_requirements=0, total_requirements=0)

    skills        = [s.name for s in candidate.skills]
    languages     = [l.name for l in candidate.languages]
    certifications = [c.name for c in candidate.certifications]
    edu_courses   = [e.course for e in candidate.educations]
    edu_insts     = [e.institution for e in candidate.educations]
    companies     = [ex.company for ex in candidate.experiences]
    location      = candidate.location

    total_weight = sum(r.weight for r in requirements)
    earned_weight = 0.0
    met = 0
    missing_mandatory: list[str] = []
    strengths: list[str] = []

    for req in requirements:
        matched = False
        if req.type == RequirementType.SKILL:
            matched = _matches(req.name, skills)
        elif req.type == RequirementType.LANGUAGE:
            matched = _matches(req.name, languages)
        elif req.type == RequirementType.CERTIFICATION:
            matched = _matches(req.name, certifications)
        elif req.type == RequirementType.EDUCATION:
            matched = _matches(req.name, edu_courses + edu_insts)
        elif req.type == RequirementType.COMPANY:
            matched = _matches(req.name, companies)
        elif req.type == RequirementType.LOCATION:
            matched = _matches(req.name, [location])

        if matched:
            earned_weight += req.weight
            met += 1
            skill = next((s for s in candidate.skills if _normalize(req.name) in _normalize(s.name) or _normalize(s.name) in _normalize(req.name)), None)
            detail = req.name
            if skill and skill.years_experience:
                detail += f" ({skill.years_experience:.0f} anos)"
            strengths.append(detail)
        else:
            if req.mandatory:
                missing_mandatory.append(req.name)

    base_score = (earned_weight / total_weight) * 100 if total_weight > 0 else 0.0
    penalty = len(missing_mandatory) * MANDATORY_PENALTY
    final_score = round(min(100.0, max(0.0, base_score * max(0.0, 1.0 - penalty))), 1)

    return ScoreResult(
        score=final_score,
        met_requirements=met,
        total_requirements=len(requirements),
        missing_mandatory=missing_mandatory,
        strengths=strengths,
    )
