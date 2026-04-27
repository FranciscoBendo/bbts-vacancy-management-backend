"""seed.py Sprint 3 — docker compose exec api python seed.py"""
from datetime import datetime
from app.database import SessionLocal
from app.models import *
from app.scoring.engine import calculate_score

def run():
    db = SessionLocal()
    try:
        for model in [IntegrationLog, CandidateSuggestion, AuditEvent, ApprovalDecision,
                      CandidateCertification, CandidateLanguage, CandidateEducation,
                      CandidateExperience, CandidateSkill, Candidate,
                      Requirement, Vacancy, User]:
            db.query(model).delete()
        db.commit()

        requester = User(id=1, name="Ana Souza", email="ana@bbts.com", role=RoleEnum.REQUESTER)
        rh = User(id=2, name="Carlos RH", email="carlos@bbts.com", role=RoleEnum.RH)
        db.add_all([requester, rh]); db.flush()

        raw = [
            {"full_name":"Rodrigo Almeida","headline":"Tech Lead Java | 10 anos em fintech","email":"rodrigo@email.com","location":"São Paulo, SP",
             "skills":[("Java","Avançado",10),("Spring Boot","Avançado",8),("Kafka","Avançado",4),("Kubernetes","Intermediário",2)],
             "langs":[("Inglês","Fluente")],"certs":[("Kubernetes CKA","CNCF",2022)],
             "edus":[("USP","Ciência da Computação","Bacharelado",2013)],
             "exps":[("FinTech XP","Tech Lead",2019,None,True),("Nubank","Senior Eng",2016,2019,False)]},
            {"full_name":"Fernanda Lima","headline":"Eng Backend Sênior | Java, Kafka","email":"fernanda@email.com","location":"São Paulo, SP",
             "skills":[("Java","Avançado",7),("Spring Boot","Avançado",6),("Kafka","Avançado",3),("Docker","Intermediário",3)],
             "langs":[("Inglês","Intermediário")],"certs":[],"edus":[("UNICAMP","Eng de Computação","Bacharelado",2016)],"exps":[("Magazine Luiza","Senior Backend",2018,None,True)]},
            {"full_name":"Bruno Martins","headline":"Dev Java Pleno | Spring Boot, AWS","email":"bruno@email.com","location":"Campinas, SP",
             "skills":[("Java","Avançado",4),("Spring Boot","Intermediário",3),("AWS","Intermediário",2)],
             "langs":[("Inglês","Básico")],"certs":[("AWS Cloud Practitioner","Amazon",2023)],"edus":[("PUC-Campinas","Sistemas de Informação","Bacharelado",2019)],"exps":[("Totvs","Dev Java Pleno",2020,None,True)]},
            {"full_name":"Juliana Costa","headline":"Backend Engineer | Python, Java","email":"juliana@email.com","location":"Recife, PE",
             "skills":[("Python","Avançado",6),("Java","Intermediário",2),("FastAPI","Avançado",3)],
             "langs":[("Inglês","Intermediário")],"certs":[],"edus":[("UFPE","Ciência da Computação","Bacharelado",2017)],"exps":[("Tempest","Backend Eng",2018,None,True)]},
            {"full_name":"Lucas Ferreira","headline":"Engenheiro de Dados | Python, Spark, dbt","email":"lucas@email.com","location":"Remoto",
             "skills":[("Python","Avançado",5),("Apache Spark","Avançado",3),("dbt","Intermediário",2),("SQL","Avançado",6)],
             "langs":[("Inglês","Avançado")],"certs":[("AWS Cloud Practitioner","Amazon",2022)],"edus":[("UFMG","Ciência da Computação","Bacharelado",2018)],"exps":[("Semantix","Data Engineer Sr",2020,None,True)]},
            {"full_name":"Camila Rocha","headline":"Dev Frontend Sênior | React, TypeScript","email":"camila@email.com","location":"São Paulo, SP",
             "skills":[("React","Avançado",6),("TypeScript","Avançado",4),("Design System / Storybook","Avançado",3)],
             "langs":[("Inglês","Intermediário")],"certs":[],"edus":[("FIAP","Análise e Desenvolvimento","Tecnólogo",2017)],"exps":[("iFood","Frontend Sr",2020,None,True)]},
        ]

        objs = []
        for cd in raw:
            c = Candidate(full_name=cd["full_name"], headline=cd["headline"], email=cd["email"], location=cd["location"])
            db.add(c); db.flush()
            for n,l,y in cd["skills"]: db.add(CandidateSkill(candidate_id=c.id, name=n, level=l, years_experience=y))
            for n,l in cd["langs"]: db.add(CandidateLanguage(candidate_id=c.id, name=n, level=l))
            for n,i,y in cd["certs"]: db.add(CandidateCertification(candidate_id=c.id, name=n, issuer=i, year=y))
            for inst,course,deg,grad in cd["edus"]: db.add(CandidateEducation(candidate_id=c.id, institution=inst, course=course, degree=deg, graduation_year=grad))
            for comp,role,s,e,cur in cd["exps"]: db.add(CandidateExperience(candidate_id=c.id, company=comp, role=role, start_year=s, end_year=e, current=cur))
            objs.append(c)
        db.flush()

        v1 = Vacancy(title="Desenvolvedor Frontend Sênior", description="Liderar design system.", location="São Paulo, SP (Híbrido)", priority=PriorityEnum.HIGH, status=VacancyStatus.DRAFT, requester_id=1, created_at=datetime(2024,6,1,9,0), updated_at=datetime(2024,6,1,9,0))
        db.add(v1); db.flush()
        db.add_all([Requirement(vacancy_id=v1.id, type=RequirementType.SKILL, name="React", weight=3.0, mandatory=True),
                    Requirement(vacancy_id=v1.id, type=RequirementType.SKILL, name="TypeScript", weight=2.0, mandatory=True),
                    Requirement(vacancy_id=v1.id, type=RequirementType.SKILL, name="Design System / Storybook", weight=1.5, mandatory=False),
                    Requirement(vacancy_id=v1.id, type=RequirementType.LANGUAGE, name="Inglês", weight=1.0, mandatory=False)])

        v2 = Vacancy(title="Engenheiro de Dados Pleno", description="Pipelines e dashboards.", location="Remoto", priority=PriorityEnum.MEDIUM, status=VacancyStatus.PENDING_APPROVAL, requester_id=1, created_at=datetime(2024,6,3,10,0), updated_at=datetime(2024,6,4,8,0))
        db.add(v2); db.flush()
        db.add_all([Requirement(vacancy_id=v2.id, type=RequirementType.SKILL, name="Python", weight=3.0, mandatory=True),
                    Requirement(vacancy_id=v2.id, type=RequirementType.SKILL, name="Apache Spark", weight=2.5, mandatory=True),
                    Requirement(vacancy_id=v2.id, type=RequirementType.SKILL, name="dbt", weight=1.5, mandatory=False),
                    Requirement(vacancy_id=v2.id, type=RequirementType.CERTIFICATION, name="AWS Cloud Practitioner", weight=1.0, mandatory=False),
                    Requirement(vacancy_id=v2.id, type=RequirementType.EDUCATION, name="Ciência da Computação", weight=1.0, mandatory=False)])
        db.add(AuditEvent(actor_user_id=1, action="VACANCY_SUBMITTED", entity_type="Vacancy", entity_id=v2.id, metadata_json={}))

        v3 = Vacancy(title="Tech Lead Backend (Java / Spring)", description="Liderança técnica do squad de pagamentos.", location="São Paulo, SP (Presencial)", priority=PriorityEnum.CRITICAL, status=VacancyStatus.APPROVED, requester_id=1, created_at=datetime(2024,5,20,9,0), updated_at=datetime(2024,5,23,14,0))
        db.add(v3); db.flush()
        db.add_all([Requirement(vacancy_id=v3.id, type=RequirementType.SKILL, name="Java", weight=3.0, mandatory=True),
                    Requirement(vacancy_id=v3.id, type=RequirementType.SKILL, name="Spring Boot", weight=3.0, mandatory=True),
                    Requirement(vacancy_id=v3.id, type=RequirementType.SKILL, name="Kafka", weight=2.0, mandatory=True),
                    Requirement(vacancy_id=v3.id, type=RequirementType.SKILL, name="Kubernetes", weight=1.5, mandatory=False),
                    Requirement(vacancy_id=v3.id, type=RequirementType.LANGUAGE, name="Inglês", weight=1.0, mandatory=False)])
        db.add(ApprovalDecision(vacancy_id=v3.id, rh_user_id=2, decision=DecisionEnum.APPROVED, justification="Vaga estratégica Q3.", decided_at=datetime(2024,5,23,14,0)))
        db.add(AuditEvent(actor_user_id=2, action="VACANCY_APPROVED", entity_type="Vacancy", entity_id=v3.id, metadata_json={}))
        db.flush(); db.refresh(v3)

        for c in objs:
            db.refresh(c)
            r = calculate_score(c, v3)
            db.add(CandidateSuggestion(vacancy_id=v3.id, candidate_id=c.id, score=r.score, explanation_json=r.to_explanation_json()))

        db.add(IntegrationLog(source="JSON", filename="seed.json", status=IntegrationStatus.SUCCESS, total_records=len(raw), success_count=len(raw), error_count=0))
        db.commit()
        print(f"✅ Seed Sprint 3 concluído! {len(raw)} candidatos, 3 vagas.")
    except Exception as e:
        db.rollback(); print(f"❌ {e}"); raise
    finally:
        db.close()

if __name__ == "__main__":
    run()
