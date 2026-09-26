"""create initial tables (T-194)

Revision ID: 20260926_1740_t194
Revises:
Create Date: 2026-09-26 17:40:00.000000

T-194: создаёт таблицы actuals / predictions / feature_toggles /
zero_overrides / prediction_runs. Seed defaults. TimescaleDB hypertable
для actuals (clinerule 18 DBML).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260926_1740_t194"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # === actuals (historical boardings) ===
    op.create_table(
        "actuals",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("route_id", sa.Integer(), nullable=False, index=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
    )
    op.create_index("ix_actuals_route_period", "actuals", ["route_id", "period_start"])

    # === predictions ===
    op.create_table(
        "predictions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("route_id", sa.Integer(), nullable=False, index=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("horizon", sa.String(16), nullable=False),
        sa.Column("granularity", sa.String(16), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("lower", sa.Float(), nullable=True),
        sa.Column("upper", sa.Float(), nullable=True),
        sa.Column("model_id", sa.String(64), nullable=False, index=True),
        sa.Column("model_kind", sa.String(32), nullable=False),
        sa.Column("model_version", sa.String(32), nullable=False),
        sa.Column("feature_set", sa.String(64), nullable=False, server_default="baseline"),
        sa.Column("feature_flags", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("zeros_applied", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("zero_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("coef_weather", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("coef_event", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("coef_season", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("submission_id", sa.String(64), nullable=True, index=True),
        sa.Column("git_commit", sa.String(40), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_predictions_route_period", "predictions", ["route_id", "period_start"])
    op.create_index("ix_predictions_model_feature", "predictions", ["model_id", "feature_set"])
    op.create_index("ix_predictions_submission", "predictions", ["submission_id"])

    # === feature_toggles ===
    op.create_table(
        "feature_toggles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(64), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    # Seed дефолтные toggles (соответствует ml/configs/feature_flags.yaml, T-174)
    # Используем 1/0 для boolean — Postgres-совместимо + sqlite-совместимо
    op.execute(
        """
        INSERT INTO feature_toggles (name, description, enabled, is_default) VALUES
          ('use_poi', 'POI features (T-168: schools, malls, parks)', 1, 1),
          ('use_traffic', 'Traffic features (T-124: OSM intersections)', 0, 0),
          ('use_weather', 'Weather features (T-123: temperature, precip)', 1, 1),
          ('use_events', 'Events calendar (T-172: infrastructure openings)', 1, 1),
          ('use_seasonal', 'Seasonal calendar (holidays, vacations)', 1, 1),
          ('use_lag', 'Lag features (T-152: per-route historical lag)', 1, 1)
        """
    )

    # === zero_overrides ===
    op.create_table(
        "zero_overrides",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(64), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("params", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    # Seed: route 5 + night hours = ON как в F-051/F-060 best
    op.execute(
        """
        INSERT INTO zero_overrides (name, description, enabled, params) VALUES
          ('zero_route_5', 'Zero out route 5 (F-051: cold start)',
           1, '{"route_id": 5}'),
          ('zero_night_pred_cap', 'Zero night hours when pred <= cap (F-060)',
           1, '{"pred_cap": 55, "hours": [0, 1, 2, 3, 4]}'),
          ('zero_weekend', 'Zero weekend boardings (T-180 — UNTESTED)',
           0, '{"weekday_in": [5, 6]}'),
          ('zero_holidays', 'Zero federal holidays (T-180 — UNTESTED)',
           0, '{"holiday_multiplier": 0.0}')
        """
    )

    # === prediction_runs ===
    op.create_table(
        "prediction_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("celery_task_id", sa.String(64), unique=True, nullable=False),
        sa.Column("task_name", sa.String(64), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("submission_id", sa.String(64), nullable=True, index=True),
        sa.Column("model_id", sa.String(64), nullable=True),
        sa.Column("feature_set", sa.String(64), nullable=True),
        sa.Column("params", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("holdout_wape_score", sa.Float(), nullable=True),
        sa.Column("manifest_path", sa.String(256), nullable=True),
        sa.Column("csv_path", sa.String(256), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )

    # === TimescaleDB hypertable для actuals (best-effort) ===
    # clinerule 18: DBML schema as code + hypertable для эффективных time-range queries.
    # Skip на sqlite/не-Postgres: DO block использует PL/pgSQL, недоступный в sqlite.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb') THEN
                    CREATE EXTENSION IF NOT EXISTS timescaledb;
                    PERFORM create_hypertable(
                        'actuals', 'period_start',
                        chunk_time_interval => INTERVAL '7 days',
                        if_not_exists => TRUE
                    );
                END IF;
            END
            $$;
            """
        )


def downgrade() -> None:
    op.drop_table("prediction_runs")
    op.drop_table("zero_overrides")
    op.drop_table("feature_toggles")
    op.drop_index("ix_predictions_submission", table_name="predictions")
    op.drop_index("ix_predictions_model_feature", table_name="predictions")
    op.drop_index("ix_predictions_route_period", table_name="predictions")
    op.drop_table("predictions")
    op.drop_index("ix_actuals_route_period", table_name="actuals")
    op.drop_table("actuals")
