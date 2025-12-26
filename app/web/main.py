from typing import List, Dict

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Budget Dashboard")

templates = Jinja2Templates(directory="app/web/templates")
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")


BUDGET_LINES: List[Dict[str, float]] = [
    {"name": "Housing", "allocated": 1800, "spent": 1450},
    {"name": "Transportation", "allocated": 450, "spent": 310},
    {"name": "Groceries", "allocated": 650, "spent": 480},
    {"name": "Dining Out", "allocated": 240, "spent": 180},
    {"name": "Entertainment", "allocated": 200, "spent": 95},
    {"name": "Savings", "allocated": 800, "spent": 600},
]

SUMMARY_CARD = {
    "status": "On Track",
    "kicker": "Monthly Health",
    "meta": "Spending 68% of allocation",
}

TRANSACTIONS = [
    {"description": "Grocery run", "account": "Checking", "amount": -82.55, "date": "Apr 17"},
    {"description": "Rent", "account": "Checking", "amount": -1450.00, "date": "Apr 1"},
    {"description": "Gym membership", "account": "Credit", "amount": -45.00, "date": "Apr 12"},
    {"description": "Paycheck", "account": "Checking", "amount": 2800.00, "date": "Apr 15"},
]

ACCOUNTS = [
    {"name": "Checking", "balance": 1850.24},
    {"name": "Savings", "balance": 4620.10},
    {"name": "Credit", "balance": -320.14},
]

SYNC_ACTIONS = [
    {"label": "Chase", "status": "Ready", "action": "Manual sync"},
    {"label": "Savings", "status": "Synced", "action": "Refresh in 24h"},
    {"label": "Brokerage", "status": "Needs login", "action": "Re-authenticate"},
]


def _base_context() -> Dict:
    return {
        "budget_lines": BUDGET_LINES,
        "summary": SUMMARY_CARD,
        "transactions": TRANSACTIONS,
        "accounts": ACCOUNTS,
        "sync_actions": SYNC_ACTIONS,
    }


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request, **_base_context()})


@app.get("/budget-lines", response_class=HTMLResponse)
def budget_lines(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("partials/budget_lines.html", {"request": request, **_base_context()})


@app.get("/summary", response_class=HTMLResponse)
def summary_card(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("partials/summary_card.html", {"request": request, **_base_context()})


@app.get("/explorer", response_class=HTMLResponse)
def explorer_panel(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("partials/explorer.html", {"request": request, **_base_context()})


@app.get("/explorer/search", response_class=HTMLResponse)
def explorer_search(request: Request, q: str = "") -> HTMLResponse:
    query = q.lower().strip()
    filtered = [
        tx
        for tx in TRANSACTIONS
        if query in tx["description"].lower()
        or query in tx["account"].lower()
        or query in tx["date"].lower()
    ] if query else TRANSACTIONS
    context = {"request": request, **_base_context(), "transactions": filtered, "query": q}
    return templates.TemplateResponse("partials/explorer.html", context)
