"""Planning Benchmark — Agents collaboratively plan a software project."""

from harness.base import BenchmarkTask


def get_task() -> BenchmarkTask:
    return BenchmarkTask(
        id="planning_01",
        name="Planning",
        description=(
            "Collaboratively plan the architecture and implementation of a multi-tenant "
            "SaaS application for AI-powered document processing. The plan should cover: "
            "architecture decisions, technology choices, data model, API design, security, "
            "deployment, and a phased implementation roadmap."
        ),
        input_data=(
            "Plan a multi-tenant SaaS application with these requirements:\n\n"
            "1. **Core Feature**: Users upload documents (PDF, DOCX), the system extracts "
            "text, generates summaries, answers questions about the documents using RAG.\n\n"
            "2. **Multi-tenancy**: Each tenant has isolated data. Tenants can have multiple "
            "users with role-based access (admin, editor, viewer).\n\n"
            "3. **Scale Target**: 100 tenants, 1000 users, 10,000 documents per tenant.\n\n"
            "4. **Tech Constraints**: Python backend, React frontend, PostgreSQL database, "
            "must run on AWS.\n\n"
            "5. **Timeline**: MVP in 8 weeks, full product in 16 weeks.\n\n"
            "6. **Budget**: Small team (2 backend, 1 frontend, 1 DevOps).\n\n"
            "Produce a comprehensive plan that a development team could execute."
        ),
        expected_aspects=[
            "Architecture: clear separation of concerns (API, processing, storage, AI)",
            "Multi-tenancy: row-level security or schema-per-tenant decision with justification",
            "Data model: documents, chunks, embeddings, users, tenants, conversations",
            "RAG pipeline: chunking strategy, embedding model choice, vector store",
            "API design: RESTful endpoints for documents, conversations, admin",
            "Security: authentication (JWT/OAuth), authorization (RBAC), data isolation",
            "Deployment: containerized (Docker), orchestrated (ECS/EKS), CI/CD pipeline",
            "Cost estimation: AWS services, AI API costs per tenant",
            "Phase 1 (MVP): single-tenant, basic upload + RAG",
            "Phase 2: multi-tenancy, RBAC, production deployment",
            "Phase 3: advanced features (analytics, fine-tuning, compliance)",
            "Risk identification: vendor lock-in, cost scaling, data privacy",
        ],
        evaluation_rubric={
            "completeness": "Does the plan cover all 6 requirement areas? (architecture, multi-tenancy, API, security, deployment, roadmap)",
            "technical_depth": "Are technology choices justified with trade-offs? Not just 'use X' but 'use X because Y, despite Z'",
            "feasibility": "Is the plan realistic for the team size and timeline?",
            "actionability": "Could a developer actually follow this plan? Are tasks specific enough?",
            "risk_awareness": "Does it identify risks and mitigation strategies?",
        },
        max_rounds=5,
        max_tokens=40000,
    )
