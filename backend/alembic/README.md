# Alembic Database Migrations

This directory contains Alembic database migrations for the AI Meeting Intelligence Platform.

## Setup

Alembic is already configured and ready to use. The configuration is in `alembic.ini` at the project root.

## Common Commands

All commands should be run from the project root directory:

### Create a new migration

```bash
# Auto-generate migration from model changes
venv_local\Scripts\python.exe -m alembic -c alembic.ini revision --autogenerate -m "Description of changes"

# Create empty migration (for manual changes)
venv_local\Scripts\python.exe -m alembic -c alembic.ini revision -m "Description of changes"
```

### Apply migrations

```bash
# Upgrade to latest version
venv_local\Scripts\python.exe -m alembic -c alembic.ini upgrade head

# Upgrade by one version
venv_local\Scripts\python.exe -m alembic -c alembic.ini upgrade +1

# Upgrade to specific version
venv_local\Scripts\python.exe -m alembic -c alembic.ini upgrade <revision_id>
```

### Rollback migrations

```bash
# Downgrade by one version
venv_local\Scripts\python.exe -m alembic -c alembic.ini downgrade -1

# Downgrade to specific version
venv_local\Scripts\python.exe -m alembic -c alembic.ini downgrade <revision_id>

# Downgrade all migrations
venv_local\Scripts\python.exe -m alembic -c alembic.ini downgrade base
```

### View migration history

```bash
# Show current version
venv_local\Scripts\python.exe -m alembic -c alembic.ini current

# Show migration history
venv_local\Scripts\python.exe -m alembic -c alembic.ini history

# Show pending migrations
venv_local\Scripts\python.exe -m alembic -c alembic.ini heads
```

## Migration Files

Migration files are stored in `backend/alembic/versions/`. Each file contains:
- `upgrade()`: SQL commands to apply the migration
- `downgrade()`: SQL commands to rollback the migration

## Important Notes

1. **Always review auto-generated migrations** before applying them
2. **Test migrations** on a development database first
3. **Backup your database** before running migrations in production
4. **Never edit applied migrations** - create a new migration instead
5. **Commit migration files** to version control

## Current Migrations

- `dd962e67b7fc`: Add live meeting fields to transcript model
  - Adds `confidence` (Float) field
  - Adds `language` (String, max 10 chars) field
  - Adds `is_final` (Boolean) field

## Troubleshooting

### Migration conflicts
If you have multiple developers creating migrations, you may encounter conflicts. Use:
```bash
venv_local\Scripts\python.exe -m alembic -c alembic.ini merge heads -m "Merge migrations"
```

### Reset migrations (development only)
```bash
# WARNING: This will drop all tables!
venv_local\Scripts\python.exe -m alembic -c alembic.ini downgrade base
venv_local\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

### Database connection issues
Ensure your `.env` file has the correct database credentials:
```
DB_HOST=localhost
DB_PORT=5433
DB_NAME=ai_meeting
DB_USER=DevM
DB_PASSWORD=pass@123
```
