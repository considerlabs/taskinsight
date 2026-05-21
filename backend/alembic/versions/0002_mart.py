"""0002 mart tables (fct_*, dim_*)

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # dim_status: Redmine 상태 → Flow 단계 매핑
    op.create_table(
        "dim_status",
        sa.Column("status_id", sa.Integer(), primary_key=True),
        sa.Column("status_name", sa.String(255)),
        sa.Column("flow_stage", sa.String(100)),  # backlog / in_progress / review / done / blocked
        sa.Column("is_closed", sa.Boolean(), server_default="false"),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
    )

    # dim_project: 프로젝트 차원 테이블
    op.create_table(
        "dim_project",
        sa.Column("project_id", sa.Integer(), primary_key=True),
        sa.Column("identifier", sa.String(255)),
        sa.Column("name", sa.String(255)),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
    )

    # dim_user: 구성원 차원 테이블
    op.create_table(
        "dim_user",
        sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("login", sa.String(255)),
        sa.Column("display_name", sa.String(255)),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
    )

    # fct_issue_snapshot: 이슈 현재 상태 스냅샷
    op.create_table(
        "fct_issue_snapshot",
        sa.Column("issue_id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer()),
        sa.Column("subject", sa.Text()),
        sa.Column("current_status_id", sa.Integer()),
        sa.Column("flow_stage", sa.String(100)),
        sa.Column("assigned_to_id", sa.Integer()),
        sa.Column("created_on", sa.DateTime(timezone=True)),
        sa.Column("updated_on", sa.DateTime(timezone=True)),
        sa.Column("closed_on", sa.DateTime(timezone=True)),
        sa.Column("total_days", sa.Float()),           # 생성→현재(또는 완료) 일수
        sa.Column("days_in_stage", sa.Float()),         # 현재 단계 체류일
        sa.Column("risk_score", sa.Integer()),          # 0~100
        sa.Column("is_rework", sa.Boolean(), server_default="false"),
        sa.Column("_etl_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fct_issue_snapshot_project_id", "fct_issue_snapshot", ["project_id"])
    op.create_index("ix_fct_issue_snapshot_flow_stage", "fct_issue_snapshot", ["flow_stage"])
    op.create_index("ix_fct_issue_snapshot_risk_score", "fct_issue_snapshot", ["risk_score"])

    # fct_state_transition: 상태 전환 이력
    op.create_table(
        "fct_state_transition",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("issue_id", sa.Integer(), nullable=False),
        sa.Column("journal_id", sa.Integer()),
        sa.Column("from_status_id", sa.Integer()),
        sa.Column("to_status_id", sa.Integer()),
        sa.Column("from_stage", sa.String(100)),
        sa.Column("to_stage", sa.String(100)),
        sa.Column("changed_at", sa.DateTime(timezone=True)),
        sa.Column("days_in_from", sa.Float()),          # 이전 단계 체류일
        sa.Column("changed_by_id", sa.Integer()),
    )
    op.create_index("ix_fct_state_transition_issue_id", "fct_state_transition", ["issue_id"])
    op.create_index("ix_fct_state_transition_changed_at", "fct_state_transition", ["changed_at"])

    # fct_throughput_daily: 일별 완료량 (TimescaleDB hypertable)
    op.create_table(
        "fct_throughput_daily",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("completed_count", sa.Integer(), server_default="0"),
        sa.Column("_etl_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_primary_key(
        "pk_fct_throughput_daily", "fct_throughput_daily", ["date", "project_id"]
    )

    # fct_assignee_workload: 구성원별 진행 중 업무 수
    op.create_table(
        "fct_assignee_workload",
        sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("in_progress_count", sa.Integer(), server_default="0"),
        sa.Column("review_count", sa.Integer(), server_default="0"),
        sa.Column("total_wip", sa.Integer(), server_default="0"),
        sa.Column("_etl_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 기본 dim_status 시드 (Redmine 기본 상태)
    op.execute("""
        INSERT INTO dim_status (status_id, status_name, flow_stage, is_closed, sort_order) VALUES
        (1,  '신규',        'backlog',      false, 1),
        (2,  '진행 중',     'in_progress',  false, 2),
        (3,  '해결됨',      'review',       false, 3),
        (4,  '피드백',      'review',       false, 4),
        (5,  '종료',        'done',         true,  5),
        (6,  '반려됨',      'done',         true,  6),
        (7,  '보류됨',      'blocked',      false, 7)
        ON CONFLICT (status_id) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_table("fct_assignee_workload")
    op.drop_table("fct_throughput_daily")
    op.drop_index("ix_fct_state_transition_changed_at", "fct_state_transition")
    op.drop_index("ix_fct_state_transition_issue_id", "fct_state_transition")
    op.drop_table("fct_state_transition")
    op.drop_index("ix_fct_issue_snapshot_risk_score", "fct_issue_snapshot")
    op.drop_index("ix_fct_issue_snapshot_flow_stage", "fct_issue_snapshot")
    op.drop_index("ix_fct_issue_snapshot_project_id", "fct_issue_snapshot")
    op.drop_table("fct_issue_snapshot")
    op.drop_table("dim_user")
    op.drop_table("dim_project")
    op.drop_table("dim_status")
