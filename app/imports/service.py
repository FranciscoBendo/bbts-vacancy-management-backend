import csv, io
from sqlalchemy.orm import Session
from app.models import (
    Candidate, CandidateSkill, CandidateExperience, CandidateEducation,
    CandidateLanguage, CandidateCertification, IntegrationLog, IntegrationStatus,
)
from app.imports.schemas import CandidateIn
from app.synonyms.dictionary import normalize_skill

def _normalize_data(data: CandidateIn) -> CandidateIn:
    return data.model_copy(update={
        "skills": [s.model_copy(update={"name": normalize_skill(s.name)}) for s in data.skills],
        "languages": [l.model_copy(update={"name": normalize_skill(l.name)}) for l in data.languages],
    })

def _upsert(db: Session, data: CandidateIn) -> Candidate:
    data = _normalize_data(data)
    c = db.query(Candidate).filter(Candidate.email == data.email).first() if data.email else None
    if c:
        c.full_name = data.full_name; c.headline = data.headline
        c.location = data.location; c.linkedin_url = data.linkedin_url
        for attr in ["skills","experiences","educations","languages","certifications"]:
            for item in getattr(c, attr): db.delete(item)
        db.flush()
    else:
        c = Candidate(full_name=data.full_name, headline=data.headline, email=data.email, location=data.location, linkedin_url=data.linkedin_url)
        db.add(c); db.flush()
    for s in data.skills: db.add(CandidateSkill(candidate_id=c.id, **s.model_dump()))
    for e in data.experiences: db.add(CandidateExperience(candidate_id=c.id, **e.model_dump()))
    for ed in data.educations: db.add(CandidateEducation(candidate_id=c.id, **ed.model_dump()))
    for l in data.languages: db.add(CandidateLanguage(candidate_id=c.id, **l.model_dump()))
    for cert in data.certifications: db.add(CandidateCertification(candidate_id=c.id, **cert.model_dump()))
    return c

def import_from_pdf_data(db: Session, extracted: dict, filename: str) -> tuple:
    try:
        candidate = _upsert(db, CandidateIn(**extracted))
        log = IntegrationLog(source="PDF", filename=filename, status=IntegrationStatus.SUCCESS,
                             total_records=1, success_count=1, error_count=0)
        db.add(log); db.commit(); db.refresh(candidate); db.refresh(log)
        return candidate, log
    except Exception as e:
        db.rollback()
        log = IntegrationLog(source="PDF", filename=filename, status=IntegrationStatus.FAILED,
                             total_records=1, success_count=0, error_count=1,
                             errors_json=[{"row": 1, "message": str(e)}])
        db.add(log); db.commit()
        raise

def import_from_json(db: Session, records: list[dict], filename: str = "payload.json") -> IntegrationLog:
    errors, success = [], 0
    for i, record in enumerate(records):
        try: _upsert(db, CandidateIn(**record)); success += 1
        except Exception as e: errors.append({"row": i+1, "message": str(e)})
    status = IntegrationStatus.SUCCESS if not errors else IntegrationStatus.PARTIAL if success > 0 else IntegrationStatus.FAILED
    log = IntegrationLog(source="JSON", filename=filename, status=status, total_records=len(records),
                         success_count=success, error_count=len(errors), errors_json=errors or None)
    db.add(log); db.commit(); db.refresh(log)
    return log

def _split(raw: str) -> list[str]:
    return [x.strip() for x in raw.split(";") if x.strip()]

def import_from_csv(db: Session, content: bytes, filename: str = "upload.csv") -> IntegrationLog:
    errors, success = [], 0
    records = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    for i, row in enumerate(records):
        try:
            skills = [{"name": p[0].strip(), "level": p[1].strip() if len(p)>1 else None, "years_experience": float(p[2]) if len(p)>2 and p[2].strip() else None} for p in [item.split(":") for item in _split(row.get("skills",""))]]
            languages = [{"name": p[0].strip(), "level": p[1].strip() if len(p)>1 else None} for p in [item.split(":") for item in _split(row.get("languages",""))]]
            certifications = [{"name": p[0].strip(), "issuer": p[1].strip() if len(p)>1 else None, "year": int(p[2]) if len(p)>2 and p[2].strip().isdigit() else None} for p in [item.split(":") for item in _split(row.get("certifications",""))]]
            educations = [{"institution": p[0].strip(), "course": p[1].strip() if len(p)>1 else "", "degree": p[2].strip() if len(p)>2 else None, "graduation_year": int(p[3]) if len(p)>3 and p[3].strip().isdigit() else None} for p in [item.split(":") for item in _split(row.get("education",""))]]
            experiences = [{"company": p[0].strip(), "role": p[1].strip() if len(p)>1 else "", "start_year": int(p[2]) if len(p)>2 and p[2].strip().isdigit() else None, "end_year": int(p[3]) if len(p)>3 and p[3].strip().isdigit() else None, "current": p[4].strip().lower()=="true" if len(p)>4 else False} for p in [item.split(":") for item in _split(row.get("experiences",""))]]
            _upsert(db, CandidateIn(full_name=row["full_name"].strip(), headline=row.get("headline","").strip(), email=row.get("email","").strip() or None, location=row.get("location","").strip(), linkedin_url=row.get("linkedin_url","").strip() or None, skills=skills, languages=languages, certifications=certifications, educations=educations, experiences=experiences))
            success += 1
        except Exception as e: errors.append({"row": i+1, "message": str(e)})
    status = IntegrationStatus.SUCCESS if not errors else IntegrationStatus.PARTIAL if success > 0 else IntegrationStatus.FAILED
    log = IntegrationLog(source="CSV", filename=filename, status=status, total_records=len(records),
                         success_count=success, error_count=len(errors), errors_json=errors or None)
    db.add(log); db.commit(); db.refresh(log)
    return log
