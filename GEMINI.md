# SLA & Support Ticket Tracking System - GEMINI Context

This project is a Flask-based IT Service Management (ITSM) prototype focused on SLA (Service Level Agreement) management, ticket lifecycle, and manager-level KPIs.

## Project Overview

- **Core Purpose:** To demonstrate automated priority calculation, SLA tracking (response/resolution targets), and operational reporting.
- **Main Technologies:**
  - **Backend:** Python 3.12+, Flask
  - **Database:** SQLite (via Flask-SQLAlchemy)
  - **Frontend:** Jinja2 templates, Bootstrap 5, Chart.js
  - **Logic:** Custom service layer for SLA calculations and priority matrix.

## Architecture

The project follows a standard Flask Blueprint-based structure:

- `app/`: Main application package.
  - `blueprints/`: Route handlers for different domains (Admin, Auth, Dashboard, Tickets).
  - `services/`: Business logic decoupled from routes (SLA math, KPI aggregation, ticket transitions).
  - `models.py`: SQLAlchemy database models.
  - `static/` & `templates/`: UI assets and Jinja2 views.
- `run.py`: Entry point for the development server and custom Flask CLI commands.
- `config.py`: Environment-based configuration.
- `scripts/`: Standalone utility scripts for testing and database verification.

## Core Models & Business Logic

### SLA Tracking (`app/models.py`)
- **Ticket Model:** Tracks `response_due_at`, `resolution_due_at`, `on_hold_started_at`, and `total_pause_duration_seconds`.
- **SLA Policy:** Defines targets (in minutes) for each priority level (P1-P4).
- **Pausing SLA:** When a ticket status is changed to "On Hold", the SLA timer pauses. The duration spent on hold is added to the due dates once the ticket returns to "In Progress".

### Priority Matrix (`app/services/tickets.py`)
- **Incidents/Problems:** Priority is derived from **Impact** (High/Medium/Low) and **Urgency** (High/Medium/Low).
- **Service Requests:** Default to P3 unless otherwise specified.

## Development Workflow

### Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Database Management
```bash
# Initialize DB, create tables, and seed base data (Policies, Users)
python -m flask --app run.py init-db

# Seed demo tickets for dashboard visualization
python -m flask --app run.py seed-demo-data
```

### Running the Application
```bash
# Runs on http://0.0.0.0:5000 by default (Debug enabled)
python run.py
```

## Testing & Utilities
- **Location:** `scripts/` directory.
- **Approach:** Standalone scripts that import `app_context` to verify specific logic (e.g., `test_apply_sla.py`).
- **Running a test:** `python scripts/test_apply_sla.py`

## Logging
- **Manager Actions:** Tracked in `logs/manager_actions.log` using a custom logger (`app.manager`). This includes assignments and escalations.

## Conventions
- **Timestamps:** Use UTC for all database entries (`datetime.utcnow`).
- **Service Layer:** Always place complex business logic in `app/services/` rather than directly in blueprints.
- **Schema Updates:** The app includes a simple schema patcher in `app/__init__.py` to handle minor column additions (like `assigned_by_id`) without full migrations.
