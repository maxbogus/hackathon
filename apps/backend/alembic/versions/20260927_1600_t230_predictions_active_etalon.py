"""predictions active/etalon switching (T-230)

Revision ID: 20260927_1600_t230
Revises: 20260926_1740_t194
Create Date: 2026-09-27 16:00:00.000000

T-230: дашборд «Аналитик» умеет генерировать новый набор прогнозов (Celery),
грузить его в БД и подменять текущий. Требуется явный признак «активного»
набора, чтобы чтения не смешивали наборы (иначе дубли rows на каждый timestamp).

Схема:
  predictions.is_active  — набор, который сейчас отдаётся API (ровно один)
  predictions.is_etalon  — эталонный набор (никогда не удаляется; restore-etalon)
  prediction_runs        — lifecycle кандидата: running → ready → loaded/rejected

Строки НИКОГДА не удаляются: подмена = UPDATE флага (гарантия, что эталон
всегда доступен для отката).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260927_1600_t230"
down_revision: str | Sequence[str] | None = "20260926_1740_t194"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ETALON_SUBMISSION_ID = "seed-test-submission"
ETALON_ROW_COUNT = 14640
ETALON_HOLDOUT_WAPE_SCORE = 0.8751


def upgrade() -> None:
    # === predictions: active/etalon flags ===
    op.add_column(
        "predictions",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "predictions",
        sa.Column(
            "is_etalon",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index("ix_predictions_active", "predictions", ["is_active"])

    # Backfill: эталон = rows seed-скрипта (data/real/test_submission.csv).
    op.execute(
        sa.text(
            "UPDATE predictions SET is_etalon = true WHERE submission_id = :sid"
        ).bindparams(sid=ETALON_SUBMISSION_ID)
    )

    # === prediction_runs: candidate lifecycle ===
    op.add_column(
        "prediction_runs", sa.Column("pipeline_kind", sa.String(16), nullable=True)
    )
    op.add_column(
        "prediction_runs", sa.Column("row_count", sa.Integer(), nullable=True)
    )
    op.add_column(
        "prediction_runs", sa.Column("recommendation", sa.String(32), nullable=True)
    )
    op.add_column("prediction_runs", sa.Column("error", sa.Text(), nullable=True))
    op.add_column(
        "prediction_runs",
        sa.Column(
            "is_etalon",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "prediction_runs",
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Etalon run — чтобы UI мог сравнить holdout кандидата с holdout эталона
    # (clinerule 24: READY_TO_UPLOAD / WORSE_THAN_PREVIOUS / IDENTICAL_TO_PREVIOUS).
    op.execute(
        sa.text(
            """
            INSERT INTO prediction_runs (
                celery_task_id, task_name, status, submission_id, model_id,
                feature_set, params, holdout_wape_score, row_count,
                pipeline_kind, is_etalon, recommendation, started_at
            )
            SELECT
                'seed-etalon-' || :sid, 'seed.etalon', 'loaded', :sid,
                'test_submission_baseline', 'with_all', '{}'::json, :holdout,
                :rows, 'seed', true, 'READY_TO_UPLOAD', now()
            WHERE EXISTS (SELECT 1 FROM predictions WHERE submission_id = :sid)
              AND NOT EXISTS (
                  SELECT 1 FROM prediction_runs WHERE celery_task_id = 'seed-etalon-' || :sid
              )
            """
        ).bindparams(
            sid=ETALON_SUBMISSION_ID,
            holdout=ETALON_HOLDOUT_WAPE_SCORE,
            rows=ETALON_ROW_COUNT,
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM prediction_runs WHERE celery_task_id LIKE 'seed-etalon-%'")
    )
    op.drop_column("prediction_runs", "activated_at")
    op.drop_column("prediction_runs", "is_etalon")
    op.drop_column("prediction_runs", "error")
    op.drop_column("prediction_runs", "recommendation")
    op.drop_column("prediction_runs", "row_count")
    op.drop_column("prediction_runs", "pipeline_kind")

    op.drop_index("ix_predictions_active", table_name="predictions")
    op.drop_column("predictions", "is_etalon")
    op.drop_column("predictions", "is_active")
