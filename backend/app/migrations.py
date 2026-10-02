"""Non-destructive schema migration helpers (MASTER_README §57, §91).

`Base.metadata.create_all` only creates *missing* tables - it never alters
existing ones. This module adds model columns and indexes that are missing
from the live database, without ever dropping, truncating or rewriting data.
It is safe to run repeatedly.
"""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.sql.compiler import SQLCompiler

from app.models import Base


def _default_sql(col, dialect: SQLCompiler) -> str:
    """Render a DEFAULT clause for a column, or '' when none is defined."""
    server_default = col.server_default
    if server_default is None:
        # Scalar Python default: only safe to emit for literals.
        if col.default is not None and col.default.is_scalar and col.default.arg is not None:
            value = col.default.arg
            if isinstance(value, (int, float)):
                return f" DEFAULT {value}"
            if isinstance(value, str):
                escaped = value.replace("'", "''")
                return f" DEFAULT '{escaped}'"
        return ""
    arg = server_default.arg
    if isinstance(arg, str):
        # Numbers stay bare ('1'), everything else is a SQL string literal.
        if arg.replace(".", "", 1).lstrip("-").isdigit():
            return f" DEFAULT {arg}"
        escaped = arg.replace("'", "''")
        return f" DEFAULT '{escaped}'"
    try:
        compiled = str(arg.compile(dialect=dialect, compile_kwargs={"literal_binds": True}))
        return f" DEFAULT {compiled}"
    except Exception:
        return ""


def ensure_schema(engine: Engine, logger=print) -> None:
    """Create missing tables, then add any missing columns/indexes."""
    # 1) create tables that do not exist yet (fully defined)
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    dialect = engine.dialect
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue

            existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
            for col in table.columns:
                if col.name in existing_cols:
                    continue
                type_sql = col.type.compile(dialect=dialect)
                parts = [f"ALTER TABLE `{table.name}` ADD COLUMN `{col.name}` {type_sql}"]
                default_sql = _default_sql(col, dialect)
                if default_sql:
                    parts.append(default_sql.strip())
                if not col.nullable:
                    parts.append("NOT NULL")
                ddl = " ".join(parts)
                conn.exec_driver_sql(ddl)
                logger(f"  + column {table.name}.{col.name}")

            # indexes (create_all does not add indexes to pre-existing tables)
            existing_indexes = inspector.get_indexes(table.name)
            existing_index_names = {i["name"] for i in existing_indexes}
            existing_index_cols = {tuple(i["column_names"] or ()) for i in existing_indexes}
            for col in table.columns:
                if not col.index or col.primary_key:
                    continue
                if (col.name,) in existing_index_cols:
                    continue
                index_name = f"ix_{table.name}_{col.name}"
                if index_name in existing_index_names:
                    continue
                conn.exec_driver_sql(
                    f"CREATE INDEX `{index_name}` ON `{table.name}` (`{col.name}`)"
                )
                logger(f"  + index {index_name}")
