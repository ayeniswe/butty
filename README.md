# Butty

Budget dashboard built with FastAPI, SQLAlchemy, and Jinja2 templates. This guide helps you get the project running quickly and points to common pitfalls.

## Prerequisites
- Python 3.12+
- SQLite (included with Python)
- `git`

## Quickstart
1. **Clone and enter the project**
   ```bash
   git clone <your-fork-url> && cd butty
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e .
   # For local development extras (linting, tests, formatting)
   pip install -e '.[dev]'
   ```

4. **Run the web app**
   ```bash
   uvicorn apps.web.main:app --reload
   ```
   - The server starts on `http://127.0.0.1:8000`.
   - A SQLite database is created automatically at `<repo>/butty.sqlite`. Override the location with `BUTTY_DB_PATH=/custom/path/butty.sqlite`.

5. **Explore the UI**
   Open your browser to `http://127.0.0.1:8000/` to see the dashboard, budgets, and transactions. Static assets and templates live under `apps/web/`.

## Project layout highlights
- `apps/web/main.py`: FastAPI app setup, routes, and template rendering.
- `core/`: service layer, data models, and integrations.
- `schema/`: SQL scripts for initializing the SQLite database used on startup.
- `tests/`: automated tests (pytest).

## Testing & quality checks
- Run the test suite:
  ```bash
  pytest
  ```
- Lint/format with Ruff:
  ```bash
  ruff check .
  ruff format .
  ```
- Template linting (optional):
  ```bash
  djlint apps/web/templates --check
  ```

## FAQ
**Where does the database live?**
The default database is `butty.sqlite` in the project root. Set `BUTTY_DB_PATH` before starting Uvicorn to store it elsewhere.

**Tables are missing or the DB is empty. What now?**
The FastAPI startup process executes SQL files in `schema/` automatically. Remove any existing DB file and restart the server to recreate tables.

**Uvicorn/ruff/pytest commands are missing.**
Ensure you installed development extras with `pip install -e '.[dev]'` and that your virtual environment is active.

**SQLite says the database is locked.**
Stop other running app instances, then restart the server. For shared filesystems, move the DB to a local path with `BUTTY_DB_PATH`.

## Contributing
We welcome contributions!
1. Fork and create a feature branch.
2. Set up the dev environment with `pip install -e '.[dev]'`.
3. Make changes with accompanying tests and keep code formatted (`ruff format .` and `ruff check .`).
4. Run `pytest` before opening a pull request.
5. Open a PR describing the change and any setup notes.

Thank you for helping improve Butty!
