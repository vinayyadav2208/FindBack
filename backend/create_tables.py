"""Create database tables and non-destructively add any missing columns.

Safe to run repeatedly; never drops or truncates anything.
"""

from app.database import engine
from app.migrations import ensure_schema

print("Creating / updating schema (non-destructive)...")
ensure_schema(engine, logger=lambda message: print(message))
print("Tables created successfully!")
