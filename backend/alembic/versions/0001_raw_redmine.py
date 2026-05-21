"""0001 raw_redmine tables

Revision ID: 0001
Revises:
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")

    op.create_table(
        "raw_redmine_projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("identifier", sa.String(255)),
        sa.Column("name", sa.String(255)),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.Integer()),
        sa.Column("is_public", sa.Boolean()),
        sa.Column("created_on", sa.DateTime(timezone=True)),
        sa.Column("updated_on", sa.DateTime(timezone=True)),
        sa.Column("payload", postgresql.JSON()),
        sa.Column("_synced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "raw_redmine_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("login", sa.String(255)),
        sa.Column("firstname", sa.String(255)),
        sa.Column("lastname", sa.String(255)),
        sa.Column("mail", sa.String(255)),
        sa.Column("status", sa.Integer()),
        sa.Column("created_on", sa.DateTime(timezone=True)),
        sa.Column("updated_on", sa.DateTime(timezone=True)),
        sa.Column("payload", postgresql.JSON()),
        sa.Column("_synced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "raw_redmine_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer()),
        sa.Column("name", sa.String(255)),
        sa.Column("status", sa.String(50)),
        sa.Column("due_date", sa.Date()),
        sa.Column("description", sa.Text()),
        sa.Column("created_on", sa.DateTime(timezone=True)),
        sa.Column("updated_on", sa.DateTime(timezone=True)),
        sa.Column("payload", postgresql.JSON()),
        sa.Column("_synced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "raw_redmine_issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer()),
        sa.Column("tracker_id", sa.Integer()),
        sa.Column("status_id", sa.Integer()),
        sa.Column("priority_id", sa.Integer()),
        sa.Column("author_id", sa.Integer()),
        sa.Column("assigned_to_id", sa.Integer()),
        sa.Column("fixed_version_id", sa.Integer()),
        sa.Column("parent_id", sa.Integer()),
        sa.Column("subject", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("start_date", sa.Date()),
        sa.Column("due_date", sa.Date()),
        sa.Column("done_ratio", sa.Integer()),
        sa.Column("estimated_hours", sa.Float()),
        sa.Column("spent_hours", sa.Float()),
        sa.Column("created_on", sa.DateTime(timezone=True)),
        sa.Column("updated_on", sa.DateTime(timezone=True)),
        sa.Column("closed_on", sa.DateTime(timezone=True)),
        sa.Column("payload", postgresql.JSON()),
        sa.Column("_synced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_raw_redmine_issues_project_id", "raw_redmine_issues", ["project_id"])
    op.create_index("ix_raw_redmine_issues_status_id", "raw_redmine_issues", ["status_id"])
    op.create_index("ix_raw_redmine_issues_updated_on", "raw_redmine_issues", ["updated_on"])

    op.create_table(
        "raw_redmine_journals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("journalized_id", sa.Integer(), nullable=False),
        sa.Column("journalized_type", sa.String(50), server_default="Issue"),
        sa.Column("user_id", sa.Integer()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_on", sa.DateTime(timezone=True)),
        sa.Column("private_notes", sa.Boolean(), server_default="false"),
        sa.Column("payload", postgresql.JSON()),
        sa.Column("_synced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_raw_redmine_journals_issue_id", "raw_redmine_journals", ["journalized_id"])
    op.create_index("ix_raw_redmine_journals_created_on", "raw_redmine_journals", ["created_on"])

    op.create_table(
        "raw_redmine_time_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer()),
        sa.Column("issue_id", sa.Integer()),
        sa.Column("user_id", sa.Integer()),
        sa.Column("activity_id", sa.Integer()),
        sa.Column("hours", sa.Float()),
        sa.Column("comments", sa.Text()),
        sa.Column("spent_on", sa.Date()),
        sa.Column("created_on", sa.DateTime(timezone=True)),
        sa.Column("updated_on", sa.DateTime(timezone=True)),
        sa.Column("payload", postgresql.JSON()),
        sa.Column("_synced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # sync_state: 수집 진행 상태 추적
    op.create_table(
        "sync_state",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("resource_type", sa.String(100), nullable=False, unique=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("last_synced_id", sa.Integer()),
        sa.Column("status", sa.String(50), server_default="idle"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("sync_state")
    op.drop_table("raw_redmine_time_entries")
    op.drop_index("ix_raw_redmine_journals_created_on", "raw_redmine_journals")
    op.drop_index("ix_raw_redmine_journals_issue_id", "raw_redmine_journals")
    op.drop_table("raw_redmine_journals")
    op.drop_index("ix_raw_redmine_issues_updated_on", "raw_redmine_issues")
    op.drop_index("ix_raw_redmine_issues_status_id", "raw_redmine_issues")
    op.drop_index("ix_raw_redmine_issues_project_id", "raw_redmine_issues")
    op.drop_table("raw_redmine_issues")
    op.drop_table("raw_redmine_versions")
    op.drop_table("raw_redmine_users")
    op.drop_table("raw_redmine_projects")
