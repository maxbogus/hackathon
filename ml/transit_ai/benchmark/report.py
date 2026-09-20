"""Export BenchmarkResult list → CSV + Markdown leaderboard."""
from __future__ import annotations

import csv
from pathlib import Path

from transit_ai.benchmark.configs import BenchmarkResult


def write_report(results: list[BenchmarkResult], output_md: Path) -> None:
    """Write leaderboard to Markdown. CSV sibling gets same stem."""
    output_md.parent.mkdir(parents=True, exist_ok=True)
    sorted_results = sorted(results, key=lambda r: r.metrics.get("rmsle", float("inf")))

    md_lines = [
        f"# Benchmark Leaderboard",
        f"",
        f"Generated: {sorted_results[0].timestamp if sorted_results else 'N/A'}",
        f"Total configs: {len(results)}",
        f"",
        f"| Rank | Model | Feature set | RMSLE | MAE | MAPE % | Time (s) | Config hash |",
        f"|------|-------|-------------|-------|-----|--------|----------|-------------|",
    ]
    for i, r in enumerate(sorted_results, start=1):
        md_lines.append(
            f"| {i} | `{r.config.model_id}` | {r.config.feature_set} | "
            f"{r.metrics.get('rmsle', 0):.4f} | {r.metrics.get('mae', 0):.2f} | "
            f"{r.metrics.get('mape', 0):.2f} | {r.train_time_sec:.1f} | "
            f"`{r.config.config_hash()}` |"
        )
    md_lines.extend([
        f"",
        f"## Per-fold scores (RMSLE)",
        f"",
    ])
    for r in sorted_results:
        scores_str = ", ".join(f"{s:.4f}" for s in r.fold_scores)
        md_lines.append(f"- **{r.config.model_id}** ({r.config.feature_set}): [{scores_str}]")

    output_md.write_text("\n".join(md_lines), encoding="utf-8")

    # CSV sibling
    csv_path = output_md.with_suffix(".csv")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "rank", "model_id", "feature_set", "rmsle", "mae", "mape_pct",
            "train_time_sec", "config_hash", "git_commit", "timestamp",
        ])
        for i, r in enumerate(sorted_results, start=1):
            writer.writerow([
                i, r.config.model_id, r.config.feature_set,
                f"{r.metrics.get('rmsle', 0):.6f}",
                f"{r.metrics.get('mae', 0):.4f}",
                f"{r.metrics.get('mape', 0):.4f}",
                f"{r.train_time_sec:.2f}",
                r.config.config_hash(),
                r.git_commit,
                r.timestamp,
            ])
