# Butty

## Prerequisites
- Python 3.12+
- git
- sqlite3

## Quickstart
1. **Clone and enter the project**
   ```bash
   git clone <your-fork-url> && cd butty
   ```

2. **Start the server (auto-bootstraps venv & deps)**
   ```bash
   ./scripts/start_butty.sh
   ```

   - Automatically creates `.venv` if missing
   - Installs dependencies from `pyproject.toml`
   - Starts the FastAPI server
   - Creates the database if needed

3. **(Optional) Run in test mode**
   ```bash
   TEST_MODE=1 ./scripts/start_butty.sh
   ```
   - Uses an isolated temporary database (`dbtemp.sqlite`)
   - Safe for demos, testing, or experiments

4. **Stop the server**
   ```bash
   ./scripts/stop_butty.sh
   ```

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
The database location depends on the mode and OS:

- **Normal mode**
  - macOS: `~/Library/Application Support/butty/db.sqlite`
  - Linux: `~/.local/share/butty/db.sqlite`

- **Test mode**
  - Uses `dbtemp.sqlite` in the same directory
  - Activated via `TEST_MODE=1`

You can override the location by setting `BUTTY_DB_PATH`.

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
