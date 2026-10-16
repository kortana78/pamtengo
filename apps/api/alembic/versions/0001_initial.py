"""Initial schema: all Pamtengo entities.

Revision ID: 0001
"""

import sqlalchemy as sa

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("role", sa.String(32), nullable=False, server_default="viewer"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "companies",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("employee_range", sa.String(50), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_companies_name", "companies", ["name"])
    op.create_index("ix_companies_country", "companies", ["country"])
    op.create_index("ix_companies_industry", "companies", ["industry"])

    op.create_table(
        "leads",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "company_id",
            sa.String(32),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("job_title", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="new"),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("fit_score", sa.Integer, nullable=True),
        sa.Column("fit_explanation", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_leads_company_id", "leads", ["company_id"])
    op.create_index("ix_leads_email", "leads", ["email"])
    op.create_index("ix_leads_status", "leads", ["status"])
    op.create_index("ix_leads_email_company", "leads", ["email", "company_id"])

    op.create_table(
        "ideal_customer_profiles",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("target_industries", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("target_countries", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("company_size_preferences", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("qualification_criteria", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "lead_id", sa.String(32), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "workflow_type", sa.String(64), nullable=False, server_default="qualify_and_draft"
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="running"),
        sa.Column("input_snapshot", sa.JSON, nullable=True),
        sa.Column("output", sa.JSON, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_runs_lead_id", "agent_runs", ["lead_id"])
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])

    op.create_table(
        "agent_steps",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "agent_run_id",
            sa.String(32),
            sa.ForeignKey("agent_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_name", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ok"),
        sa.Column("input_summary", sa.Text, nullable=True),
        sa.Column("output_summary", sa.Text, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_steps_run", "agent_steps", ["agent_run_id"])

    op.create_table(
        "outreach_drafts",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "lead_id", sa.String(32), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "agent_run_id",
            sa.String(32),
            sa.ForeignKey("agent_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("evidence", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_drafts_lead", "outreach_drafts", ["lead_id"])
    op.create_index("ix_drafts_status", "outreach_drafts", ["status"])

    op.create_table(
        "activities",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "lead_id", sa.String(32), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("activity_type", sa.String(64), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("metadata", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_activities_lead", "activities", ["lead_id"])
    op.create_index("ix_activities_type", "activities", ["activity_type"])


def downgrade() -> None:
    for table in [
        "activities",
        "outreach_drafts",
        "agent_steps",
        "agent_runs",
        "ideal_customer_profiles",
        "leads",
        "companies",
        "users",
    ]:
        op.drop_table(table)
