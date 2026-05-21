"""0003 MVP additions (connector_instance, fct_issue_explanation, fct_weekly_report)

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # connector_instance: Settings용 연동 설정
    op.create_table(
        "connector_instance",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("connector_type", sa.String(50), nullable=False),   # "redmine"
        sa.Column("instance_name", sa.String(200), nullable=False),    # "사내 Redmine"
        sa.Column("config", postgresql.JSONB(), nullable=False),       # {base_url, api_key, lookback_days}
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 초기 Redmine 연동 시드 (api_key는 Settings 화면에서 입력)
    op.execute("""
        INSERT INTO connector_instance (connector_type, instance_name, config)
        VALUES ('redmine', '사내 Redmine',
                '{"base_url": "http://redmine.mannaplanet.co.kr:5555/redmine",
                  "lookback_days": 3650}'::jsonb);
    """)

    # fct_issue_explanation: LLM 설명 캐시
    op.create_table(
        "fct_issue_explanation",
        sa.Column("issue_id", sa.Integer(), primary_key=True),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("model_version", sa.String(50)),    # "qwen3.6:35b-a3b"
        sa.Column("is_stale", sa.Boolean(), server_default="false"),
    )

    # fct_weekly_report: 주간보고 저장
    op.create_table(
        "fct_weekly_report",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer()),
        sa.Column("period_start", sa.Date()),
        sa.Column("period_end", sa.Date()),
        sa.Column("throughput_current", sa.Integer()),
        sa.Column("throughput_previous", sa.Integer()),
        sa.Column("bottleneck_summary", postgresql.JSONB()),    # top 3 bottleneck
        sa.Column("forecast_p50_weeks", sa.Integer()),
        sa.Column("forecast_p85_weeks", sa.Integer()),
        sa.Column("forecast_p95_weeks", sa.Integer()),
        sa.Column("forecast_change_weeks", sa.Integer()),       # 전주 대비 변화
        sa.Column("narrative_text", sa.Text()),                 # LLM 생성 서술
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fct_weekly_report_project_period", "fct_weekly_report",
                    ["project_id", "period_start"])


def downgrade() -> None:
    op.drop_index("ix_fct_weekly_report_project_period", "fct_weekly_report")
    op.drop_table("fct_weekly_report")
    op.drop_table("fct_issue_explanation")
    op.drop_table("connector_instance")
