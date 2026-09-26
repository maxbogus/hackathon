#!/usr/bin/env python3
"""generate_dbml.py — Generate DBML schema from SQLAlchemy models.

Introspects SQLAlchemy ``Base.metadata`` and emits:
- ``docs/architecture/schema.dbml`` — DBML for https://dbdiagram.io
- ``docs/architecture/schema-tables.md`` — human-readable table list with privacy hints

Source of truth = ``apps/backend/app/models/`` (currently empty in T-001..T-013).

Usage:
    uv run python scripts/generate_dbml.py                # write artifacts
    uv run python scripts/generate_dbml.py --check         # CI gate (exit 1 on drift)

When models dir is empty, writes a "scaffold" DBML explaining how to add first model.

Source: candidate-tracker/scripts/generate_dbml.py (адаптация под Transit-AI).
"""
from __future__ import annotations

import argparse
import difflib
import importlib
import pkgutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "apps" / "backend"
MODELS_PACKAGE = "app.models"
DEFAULT_OUTPUT = ROOT / "docs" / "architecture" / "schema.dbml"
DEFAULT_TABLES_DOC = ROOT / "docs" / "architecture" / "schema-tables.md"

# Map SQLAlchemy types → DBML types
TYPE_MAP = {
    "INTEGER": "int",
    "BIGINT": "bigint",
    "SMALLINT": "smallint",
    "VARCHAR": "varchar",
    "TEXT": "text",
    "BOOLEAN": "boolean",
    "FLOAT": "float",
    "DOUBLE_PRECISION": "double",
    "NUMERIC": "numeric",
    "DECIMAL": "decimal",
    "DATE": "date",
    "DATETIME": "datetime",
    "TIMESTAMP": "timestamp",
    "JSON": "json",
    "JSONB": "jsonb",
    "UUID": "uuid",
}


def discover_models() -> list[str]:
    """Find all modules in apps/backend/app/models/ and import them."""
    models_dir = BACKEND / "app" / "models"
    if not models_dir.exists():
        return []
    sys.path.insert(0, str(BACKEND))
    found = []
    for mod_info in pkgutil.iter_modules([str(models_dir)]):
        mod_name = mod_info.name
        if mod_name.startswith("_") or mod_name in ("base", "__init__"):
            continue
        try:
            importlib.import_module(f"{MODELS_PACKAGE}.{mod_name}")
            found.append(mod_name)
        except Exception as e:
            print(f"⚠ Failed to import {mod_name}: {e}", file=sys.stderr)
    return found


def collect_metadata() -> tuple[list, dict[str, str]]:
    """Collect Table objects from Base.metadata + privacy hints from docstrings."""
    try:
        from app.models import Base  # type: ignore[import-not-found]
    except ImportError:
        return [], {}

    tables = list(Base.metadata.tables.values())
    hints: dict[str, str] = {}
    registry = getattr(Base, "registry", None)
    class_registry = getattr(registry, "_class_registry", {}) if registry else {}
    for table in tables:
        model_cls = None
        for cls in class_registry.values():
            if hasattr(cls, "__tablename__") and cls.__tablename__ == table.name:
                model_cls = cls
                break
        if model_cls and model_cls.__doc__:
            for line in model_cls.__doc__.splitlines():
                line = line.strip()
                if line.lower().startswith("privacy:"):
                    hints[table.name] = line.split(":", 1)[1].strip()
                    break
    return tables, hints


def render_dbml(tables: list, hints: dict[str, str]) -> str:
    """Render DBML schema."""
    lines = [
        "// Schema generated from apps/backend/app/models (SQLAlchemy).",
        "// Update models and run: make arch-dbml",
        "// Visualize at https://dbdiagram.io",
        "",
        "Project transit_ai {",
        "  database_type: 'PostgreSQL'",
        "  Note: 'Transit-AI — пассажиропоток трамваев Москвы. Backend: apps/backend, ML: ml/.'",
        "}",
        "",
    ]
    if not tables:
        lines.extend([
            "// No models registered yet. Phase 1 in progress.",
            "// First model: apps/backend/app/models/stop.py (T-038+)",
            "//",
            "// После добавления первой модели запусти: make arch-dbml",
            "",
        ])
        return "\n".join(lines)

    for table in tables:
        cols = []
        for col in table.columns:
            dbml_type = TYPE_MAP.get(col.type.__class__.__name__.upper(), "varchar")
            constraints = []
            if col.primary_key:
                constraints.append("pk")
            if not col.nullable:
                constraints.append("not null")
            if col.unique:
                constraints.append("unique")
            constraint_str = f" [{', '.join(constraints)}]" if constraints else ""
            cols.append(f"  {col.name} {dbml_type}{constraint_str}")
        note = f"\n  Note: '{hints[table.name]}'" if table.name in hints else ""
        lines.append(f"Table {table.name} {{")
        lines.extend(cols)
        if note:
            lines.append(note)
        lines.append("}")
        lines.append("")
    return "\n".join(lines)


def render_tables_md(tables: list, hints: dict[str, str]) -> str:
    """Render human-readable table list."""
    lines = [
        "# Schema Tables — entity & privacy overview",
        "",
        "> Generated from `apps/backend/app/models` — do not edit by hand.",
        "> Run `make arch-dbml` to regenerate.",
        "",
        "| Table | Purpose | Privacy hints | Columns |",
        "|-------|---------|---------------|---------|",
    ]
    if not tables:
        lines.append("| _(none)_ | _(no models registered yet)_ | — | — |")
        return "\n".join(lines) + "\n"

    try:
        from app.models import Base  # type: ignore[import-not-found]
        registry = getattr(Base, "registry", None)
        class_registry = getattr(registry, "_class_registry", {}) if registry else {}
    except ImportError:
        class_registry = {}

    for table in tables:
        n_cols = len(table.columns)
        purpose = ""
        for cls in class_registry.values():
            if hasattr(cls, "__tablename__") and cls.__tablename__ == table.name and cls.__doc__:
                for line in cls.__doc__.splitlines():
                    l = line.strip()
                    if l and not l.lower().startswith("privacy:"):
                        purpose = l
                        break
                break
        privacy = hints.get(table.name, "—")
        lines.append(f"| `{table.name}` | {purpose or '—'} | {privacy} | {n_cols} |")
    return "\n".join(lines) + "\n"


def write_artifacts(dbml: str, tables_md: str, output: Path, tables_doc: Path) -> None:
    """Write both artifacts."""
    output.parent.mkdir(parents=True, exist_ok=True)
    tables_doc.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(dbml)
    tables_doc.write_text(tables_md)


def check_drift(old_dbml: str, new_dbml: str, old_tables: str, new_tables: str) -> bool:
    """Return True if drift detected."""
    if old_dbml == new_dbml and old_tables == new_tables:
        return False
    print("❌ DBML drift detected!")
    for old, new, name in [
        (old_dbml, new_dbml, "schema.dbml"),
        (old_tables, new_tables, "schema-tables.md"),
    ]:
        if old != new:
            print(f"\n--- diff: {name} ---")
            for line in difflib.unified_diff(
                old.splitlines(keepends=True),
                new.splitlines(keepends=True),
                fromfile=f"a/{name}",
                tofile=f"b/{name}",
            ):
                print(line, end="")
    return True


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--tables-doc", type=Path, default=DEFAULT_TABLES_DOC)
    p.add_argument("--check", action="store_true", help="CI gate: exit 1 if drift")
    args = p.parse_args()

    discovered = discover_models()
    if discovered:
        print(f"📦 Discovered models: {discovered}")
    tables, hints = collect_metadata()
    print(f"📊 Tables in Base.metadata: {len(tables)}")

    dbml = render_dbml(tables, hints)
    tables_md = render_tables_md(tables, hints)

    if args.check:
        old_dbml = args.output.read_text() if args.output.exists() else ""
        old_tables = args.tables_doc.read_text() if args.tables_doc.exists() else ""
        if check_drift(old_dbml, dbml, old_tables, tables_md):
            print("\nFix by running: make arch-dbml")
            return 1
        print("✅ DBML in sync.")
        return 0

    write_artifacts(dbml, tables_md, args.output, args.tables_doc)
    print(f"✅ Wrote {args.output} ({len(dbml)} bytes)")
    print(f"✅ Wrote {args.tables_doc} ({len(tables_md)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
