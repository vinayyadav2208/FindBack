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

    # Columns whose model definition became MORE permissive (NOT NULL -> NULL).
    # Loosening nullability never drops or rewrites data - MySQL only updates
    # the column flag - but the list is whitelisted so no legacy table is ever
    # touched by surprise (§57, §91: additive-only, never destructive).
    nullability_loosens = {("messages", "match_id")}

    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue

            existing_cols = {c["name"]: c for c in inspector.get_columns(table.name)}
            for col in table.columns:
                if col.name not in existing_cols:
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
                    continue
                if col.nullable and (table.name, col.name) in nullability_loosens:
                    db_col = existing_cols[col.name]
                    if not db_col.get("nullable", True):
                        type_sql = col.type.compile(dialect=dialect)
                        conn.exec_driver_sql(
                            f"ALTER TABLE `{table.name}` MODIFY `{col.name}` {type_sql} NULL"
                        )
                        logger(f"  ~ column {table.name}.{col.name} now NULL")

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

            # Foreign keys for columns that reference another table. Columns
            # added by ADD COLUMN only received their index above - the
            # constraint itself must be added separately (ADD CONSTRAINT never
            # touches data). If it cannot be created (e.g. legacy orphans) we
            # log a warning and continue: startup must never fail (§57, §91).
            existing_fk_cols = {
                tuple(fk.get("constrained_columns") or ())
                for fk in inspector.get_foreign_keys(table.name)
            }
            for col in table.columns:
                if not col.foreign_keys or (col.name,) in existing_fk_cols:
                    continue
                ref = sorted(col.foreign_keys, key=lambda f: f.target_fullname)[0]
                ref_table, _, ref_col = ref.target_fullname.partition(".")
                if not ref_col or ref_table not in existing_tables:
                    continue
                try:
                    conn.exec_driver_sql(
                        f"ALTER TABLE `{table.name}` ADD CONSTRAINT "
                        f"`fk_{table.name}_{col.name}` FOREIGN KEY (`{col.name}`) "
                        f"REFERENCES `{ref_table}` (`{ref_col}`)"
                    )
                    logger(f"  + foreign key {table.name}.{col.name}")
                except Exception as exc:  # noqa: BLE001 - advisory only
                    logger(f"  ! foreign key {table.name}.{col.name} skipped: {exc}")
