"""Schema upgrades for existing SQLite installations."""
from sqlalchemy import inspect, text
from .database import engine

def migrate_database() -> None:
    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    table = next((name for name in table_names if name.lower() == "pricealert"), None)
    if table is None:
        return
    existing = {column["name"] for column in inspector.get_columns(table)}
    changes = []
    if "triggered" not in existing:
        changes.append(f'ALTER TABLE "{table}" ADD COLUMN triggered BOOLEAN NOT NULL DEFAULT 0')
    if "last_condition_met" not in existing:
        changes.append(f'ALTER TABLE "{table}" ADD COLUMN last_condition_met BOOLEAN')
    if "triggered_at" not in existing:
        changes.append(f'ALTER TABLE "{table}" ADD COLUMN triggered_at DATETIME')
    if changes:
        with engine.begin() as connection:
            for statement in changes:
                connection.execute(text(statement))
