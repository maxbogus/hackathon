"""CLI external ETL (шаг 0, T-231).

Использование:
    python -m app.build --source all                  # собрать все артефакты
    python -m app.build --source weather --out DIR    # один источник
    python -m app.build --verify                      # проверить манифест
    python -m app.build --show                        # таблица источников
"""

from __future__ import annotations

import argparse
import sys

from app.build import builders, pipeline


def build_parser() -> argparse.ArgumentParser:
    """Аргументы CLI (совпадают с make-таргетами external-*)."""
    parser = argparse.ArgumentParser(
        prog="app.build", description="External ETL: raw-источники → normalized JSON (шаг 0)"
    )
    parser.add_argument(
        "--source",
        default="all",
        help="all | " + " | ".join(builders.SOURCES),
    )
    parser.add_argument("--repo-root", default=None, help="корень репозитория (default: авто)")
    parser.add_argument("--out", default=None, help="куда писать normalized/*.json")
    parser.add_argument(
        "--source-epoch",
        default=None,
        help="фиксированный generated_at (детерминизм; default: SOURCE_DATE_EPOCH/mtime)",
    )
    parser.add_argument("--verify", action="store_true", help="проверить артефакты против манифеста")
    parser.add_argument("--show", action="store_true", help="показать таблицу источников")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI. 0 — успех, 1 — провал верификации, 2 — ошибка аргументов."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.verify:
        return pipeline.verify(out_dir=args.out)

    if args.show:
        print(pipeline.show(out_dir=args.out))
        return 0

    sources = None
    if args.source != "all":
        if args.source not in builders.BUILDERS:
            parser.error(f"unknown --source {args.source!r} (доступно: all, {', '.join(builders.SOURCES)})")
        sources = [args.source]

    summary = pipeline.build_all(
        repo_root=args.repo_root,
        out_dir=args.out,
        mode="offline",
        sources=sources,
        source_epoch=args.source_epoch,
    )

    for name, meta in summary["sources"].items():
        warning = f"  WARNING: {meta['warning']}" if meta.get("warning") else ""
        print(
            f"[{name}] rows={meta['rows_count']} "
            f"sha256={str(meta['output_sha256'])[:8]} → {meta['output_path']}{warning}"
        )
    print(f"manifest: {summary['manifest_path']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
