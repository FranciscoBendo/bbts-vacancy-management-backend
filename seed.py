"""
seed.py — Popula o banco com dados de demonstração para Sprint 1.
Executar APÓS as migrations: python seed.py
"""
from datetime import datetime
from app.database import SessionLocal
from app.models import (
    User, Vacancy, Requirement, ApprovalDecision, CandidateSuggestion, AuditEvent,
    RoleEnum, VacancyStatus, PriorityEnum, RequirementType, DecisionEnum,
)


def run():
    db = SessionLocal()
    try:
        # ── Idempotência: apaga seed anterior ──────────────────────────────────
        for model in [
            CandidateSuggestion, AuditEvent, ApprovalDecision,
            Requirement, Vacancy, User,
        ]:
            db.query(model).delete()
        db.commit()

        # ── Usuários ───────────────────────────────────────────────────────────
        requester = User(id=1, name="Ana Souza", email="ana@bbts.com", role=RoleEnum.REQUESTER)
        rh        = User(id=2, name="Carlos RH",  email="carlos@bbts.com", role=RoleEnum.RH)
        db.add_all([requester, rh])
        db.flush()

        # ── Vaga 1 — DRAFT ─────────────────────────────────────────────────────
        v1 = Vacancy(
            title="Desenvolvedor Frontend Sênior",
            description=(
                "Buscamos um dev frontend experiente para integrar o time de produto. "
                "Você irá liderar a arquitetura do novo design system e mentorar juniores."
            ),
            location="São Paulo, SP (Híbrido)",
            priority=PriorityEnum.HIGH,
            status=VacancyStatus.DRAFT,
            requester_id=requester.id,
            created_at=datetime(2024, 6, 1, 9, 0),
            updated_at=datetime(2024, 6, 1, 9, 0),
        )
        db.add(v1)
        db.flush()

        db.add_all([
            Requirement(vacancy_id=v1.id, type=RequirementType.SKILL,
                        name="React", level="Avançado", weight=3.0, mandatory=True),
            Requirement(vacancy_id=v1.id, type=RequirementType.SKILL,
                        name="TypeScript", level="Intermediário", weight=2.0, mandatory=True),
            Requirement(vacancy_id=v1.id, type=RequirementType.SKILL,
                        name="Design System / Storybook", weight=1.5, mandatory=False),
            Requirement(vacancy_id=v1.id, type=RequirementType.LANGUAGE,
                        name="Inglês", level="Intermediário", weight=1.0, mandatory=False),
        ])

        # ── Vaga 2 — PENDING_APPROVAL ──────────────────────────────────────────
        v2 = Vacancy(
            title="Engenheiro de Dados Pleno",
            description=(
                "Vaga para integrar o time de dados, responsável por pipelines de ingestão, "
                "modelagem dimensional e dashboards executivos."
            ),
            location="Remoto",
            priority=PriorityEnum.MEDIUM,
            status=VacancyStatus.PENDING_APPROVAL,
            requester_id=requester.id,
            created_at=datetime(2024, 6, 3, 10, 0),
            updated_at=datetime(2024, 6, 4, 8, 0),
        )
        db.add(v2)
        db.flush()

        db.add_all([
            Requirement(vacancy_id=v2.id, type=RequirementType.SKILL,
                        name="Python", level="Avançado", weight=3.0, mandatory=True),
            Requirement(vacancy_id=v2.id, type=RequirementType.SKILL,
                        name="Apache Spark", weight=2.5, mandatory=True),
            Requirement(vacancy_id=v2.id, type=RequirementType.SKILL,
                        name="dbt", weight=1.5, mandatory=False),
            Requirement(vacancy_id=v2.id, type=RequirementType.CERTIFICATION,
                        name="AWS Cloud Practitioner", weight=1.0, mandatory=False),
            Requirement(vacancy_id=v2.id, type=RequirementType.EDUCATION,
                        name="Ciência da Computação ou áreas afins", weight=1.0, mandatory=False),
        ])

        # Audit: submit da vaga 2
        db.add(AuditEvent(
            actor_user_id=requester.id,
            action="VACANCY_SUBMITTED",
            entity_type="Vacancy",
            entity_id=v2.id,
            metadata_json={"previous_status": "DRAFT"},
            created_at=datetime(2024, 6, 4, 8, 0),
        ))

        # ── Vaga 3 — APPROVED (com candidatos) ────────────────────────────────
        v3 = Vacancy(
            title="Tech Lead Backend (Java / Spring)",
            description=(
                "Liderança técnica do squad de pagamentos. "
                "Responsável por decisões de arquitetura, code review e evolução da plataforma."
            ),
            location="São Paulo, SP (Presencial)",
            priority=PriorityEnum.CRITICAL,
            status=VacancyStatus.APPROVED,
            requester_id=requester.id,
            created_at=datetime(2024, 5, 20, 9, 0),
            updated_at=datetime(2024, 5, 23, 14, 0),
        )
        db.add(v3)
        db.flush()

        db.add_all([
            Requirement(vacancy_id=v3.id, type=RequirementType.SKILL,
                        name="Java", level="Avançado", weight=3.0, mandatory=True),
            Requirement(vacancy_id=v3.id, type=RequirementType.SKILL,
                        name="Spring Boot", weight=3.0, mandatory=True),
            Requirement(vacancy_id=v3.id, type=RequirementType.SKILL,
                        name="Kafka", weight=2.0, mandatory=True),
            Requirement(vacancy_id=v3.id, type=RequirementType.SKILL,
                        name="Kubernetes", weight=1.5, mandatory=False),
            Requirement(vacancy_id=v3.id, type=RequirementType.LANGUAGE,
                        name="Inglês", level="Avançado", weight=1.0, mandatory=False),
        ])

        # Decision
        db.add(ApprovalDecision(
            vacancy_id=v3.id,
            rh_user_id=rh.id,
            decision=DecisionEnum.APPROVED,
            justification="Vaga estratégica para Q3. Aprovada com prioridade máxima.",
            decided_at=datetime(2024, 5, 23, 14, 0),
        ))
        db.add(AuditEvent(
            actor_user_id=rh.id,
            action="VACANCY_APPROVED",
            entity_type="Vacancy",
            entity_id=v3.id,
            metadata_json={},
            created_at=datetime(2024, 5, 23, 14, 0),
        ))

        # ── Candidatos para Vaga 3 ─────────────────────────────────────────────
        candidates_data = [
            {
                "full_name": "Rodrigo Almeida",
                "headline": "Tech Lead Java | 10 anos de experiência em sistemas de pagamento",
                "location": "São Paulo, SP",
                "score": 95.0,
                "explanation_json": {
                    "met_requirements": 5,
                    "total_requirements": 5,
                    "missing_mandatory": [],
                    "strengths": [
                        "10 anos com Java e Spring Boot em fintech",
                        "Certificado Kubernetes CKA",
                        "Inglês fluente — experiência em times internacionais",
                        "Liderou squad de 8 pessoas",
                    ],
                },
            },
            {
                "full_name": "Fernanda Lima",
                "headline": "Engenheira Backend Sênior | Java, Kafka, arquitetura de microsserviços",
                "location": "São Paulo, SP",
                "score": 82.0,
                "explanation_json": {
                    "met_requirements": 4,
                    "total_requirements": 5,
                    "missing_mandatory": [],
                    "strengths": [
                        "7 anos com Java e Spring em e-commerce de alto volume",
                        "Forte experiência com Kafka (event sourcing)",
                        "Inglês intermediário — em evolução",
                    ],
                },
            },
            {
                "full_name": "Bruno Martins",
                "headline": "Desenvolvedor Java Pleno | Spring Boot, AWS, microsserviços",
                "location": "Campinas, SP",
                "score": 61.0,
                "explanation_json": {
                    "met_requirements": 3,
                    "total_requirements": 5,
                    "missing_mandatory": ["Kafka"],
                    "strengths": [
                        "Sólido em Java e Spring Boot",
                        "Experiência com AWS (EC2, RDS, SQS)",
                        "Interesse declarado em aprender Kafka",
                    ],
                },
            },
            {
                "full_name": "Juliana Costa",
                "headline": "Backend Engineer | Python, Java, sistemas distribuídos",
                "location": "Remoto (Recife, PE)",
                "score": 44.0,
                "explanation_json": {
                    "met_requirements": 2,
                    "total_requirements": 5,
                    "missing_mandatory": ["Kafka", "Spring Boot"],
                    "strengths": [
                        "Boa base em sistemas distribuídos",
                        "Experiência com Java, porém foco em Python nos últimos 2 anos",
                    ],
                },
            },
        ]

        for c in candidates_data:
            db.add(CandidateSuggestion(vacancy_id=v3.id, **c))

        db.commit()
        print("✅  Seed concluído com sucesso!")
        print("   Usuários:  Ana (id=1, REQUESTER) | Carlos (id=2, RH)")
        print("   Vagas:     id=1 DRAFT | id=2 PENDING_APPROVAL | id=3 APPROVED (com candidatos)")

    except Exception as e:
        db.rollback()
        print(f"❌  Erro no seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
