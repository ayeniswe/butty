# Butty

Butty is a personal budgeting app with a FastAPI backend + server-rendered HTMX UI. It helps you:
- Create monthly budget categories.
- Link bank accounts with Plaid.
- Sync and explore transactions.
- Assign transactions to budgets.
- Track how much you have spent vs allocated.

---

## What you need

- Python 3.12+
- `git`
- SQLite (bundled with most Python installs)

Optional (self-hosting in containers):
- Docker **or** Podman + podman-compose

---

## 1) Quick start (local development)

### Step 1: Clone the repo

```bash
git clone <your-repo-url>
cd butty
```

### Step 2: Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install dependencies

```bash
pip install --upgrade pip
pip install -e '.[dev]'
```

### Step 4: Create your `.env` file

Create a `.env` file in the repo root:

```bash
cat > .env <<'ENVVARS'
ENV=dev
PORT=8001
BUTTY_DB_PATH=./butty.sqlite

# Plaid (required for bank-linking features)
PLAID_CLIENT=your_plaid_client_id
PLAID_SECRET=your_plaid_secret
ENVVARS
```

> `ENV=dev` uses Plaid Sandbox mode in this codebase.

### Step 5: Run the app

```bash
python apps/web/main.py
```

Then open: `http://127.0.0.1:8001/`

---

## 2) Plaid key setup (required for account linking)

Butty expects these environment variables:

- `PLAID_CLIENT`
- `PLAID_SECRET`
- `ENV`

Behavior:
- `ENV=prod` → Plaid Production
- any other value (like `dev` / `sandbox`) → Plaid Sandbox

### Plaid Sandbox (recommended first)

1. Create a Plaid developer account.
2. Create a Sandbox app in Plaid dashboard.
3. Copy Client ID + Sandbox Secret.
4. Add them to `.env` as `PLAID_CLIENT` and `PLAID_SECRET`.
5. Keep `ENV=dev` (or any non-`prod` value).

### Plaid Production

1. Complete Plaid Production setup in your Plaid dashboard.
2. Use Production Client ID/Secret.
3. Set `ENV=prod`.
4. Restart Butty.

If Plaid variables are missing, account-linking routes will fail when the app tries to initialize Plaid.

---

## 3) Main workflow: how to use Butty effectively

After launching the app, use this flow:

1. **Go to the dashboard** (`/`).
2. **Create budget items** in the left panel (for example: Groceries, Rent, Utilities).
3. Optionally use **“Use Last Month’s Budget”** to copy prior month allocations.
4. In the Activity panel, click **Add Account** to open Plaid Link and connect your bank.
5. Click **Sync** to fetch latest transactions.
6. Right-click (or use the `⋯`) on transactions to:
   - Assign to a budget
   - Remove budget assignment
   - Add/edit notes
   - Ignore for budget auto-assignment
7. Watch the budget progress bars update as spending is categorized.
8. Use search in Explorer to quickly find transactions by name/account/date/budget.

### CSV import workflow (if you are not using Plaid yet)

You can import transactions with **Import CSV** in the Activity panel.

Your CSV must contain these headers exactly:
- `Date`
- `Description`
- `Amount`
- `Account Name`
- `Budget`

Notes:
- Date should be ISO format (example: `2026-01-08`).
- Amount accepts values like `123.45` and `$123.45`.
- Rows missing required values are skipped.

---

## 4) Self-hosted deployment options

### Option A: Docker

#### Build image

```bash
docker build -t butty:latest .
```

#### Run container

```bash
docker run -d \
  --name butty \
  -p 8001:8001 \
  -e ENV=prod \
  -e PLAID_CLIENT=your_plaid_client_id \
  -e PLAID_SECRET=your_plaid_secret \
  -e BUTTY_DB_PATH=/data/butty.db \
  -v butty_data:/data \
  butty:latest
```

Open `http://<server-ip>:8001/`

#### Stop/remove

```bash
docker stop butty
docker rm butty
```

---

### Option B: Podman Compose (included in repo)

The repo includes `podman-compose.yml` with persistent volumes.

#### 1. Create env files

Create `.env.prod` (used by `butty` service):

```bash
cat > .env.prod <<'ENVVARS'
ENV=prod
PLAID_CLIENT=your_plaid_client_id
PLAID_SECRET=your_plaid_secret
PORT=8001
ENVVARS
```

Create `.env.test` (used by `butty-dev` service):

```bash
cat > .env.test <<'ENVVARS'
ENV=dev
PLAID_CLIENT=your_plaid_client_id
PLAID_SECRET=your_plaid_secret
PORT=8001
ENVVARS
```

#### 2. Start services

```bash
podman-compose up -d --build
```

- Production-like service: `http://<server-ip>:8001/`
- Dev service: `http://<server-ip>:8002/`

#### 3. Stop services

```bash
podman-compose down
```

---

## 5) Database behavior

- Default DB path when running the app script: `./butty.sqlite`
- Override with `BUTTY_DB_PATH`.
- On startup, Butty initializes schema from SQL files in `schema/`.

Examples:

```bash
# put DB in a custom location
BUTTY_DB_PATH=/var/lib/butty/butty.sqlite python apps/web/main.py
```

---

## 6) Useful dev commands

Run tests:

```bash
pytest
```

Lint + format:

```bash
ruff check .
ruff format .
```

Template lint (optional):

```bash
djlint apps/web/templates --check
```

---

## 7) Troubleshooting

### “No module named ...”
Your virtual env is not active or dependencies are missing.

```bash
source .venv/bin/activate
pip install -e '.[dev]'
```

### Plaid link/sync not working
- Verify `PLAID_CLIENT`, `PLAID_SECRET`, and `ENV` are set.
- Ensure your Plaid credentials match the environment (`dev/sandbox` vs `prod`).
- Restart the app after env changes.

### Port already in use
Use a different port:

```bash
PORT=8010 python apps/web/main.py
```

### SQLite locked
Another process may already be using the same DB file. Stop duplicate app instances or change `BUTTY_DB_PATH`.

---

## 8) Project layout

- `apps/web/main.py` – FastAPI app entrypoint and routes.
- `apps/web/templates/` – HTML templates for dashboard/activity/budgets.
- `core/service.py` – business logic for budgets, transactions, Plaid sync.
- `core/datastore/` – SQLite data access layer.
- `schema/` – SQL schema and migrations.
- `tests/` – test suite.
