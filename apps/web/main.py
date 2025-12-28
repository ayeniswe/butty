import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Budget Dashboard")

templates = Jinja2Templates(directory="apps/web/templates")
app.mount("/static", StaticFiles(directory="apps/web/static"), name="static")

BUDGET_LINES: list[dict[str, float]] = [
    {"id": "1", "name": "Housing", "allocated": 1800, "spent": 1450},
    {"id": "2", "name": "Transportation", "allocated": 450, "spent": 310},
    {"id": "3", "name": "Groceries", "allocated": 650, "spent": 480},
    {"id": "4", "name": "Dining Out", "allocated": 240, "spent": 180},
    {"id": "5", "name": "Entertainment", "allocated": 200, "spent": 95},
    {"id": "6", "name": "Savings", "allocated": 800, "spent": 600},
    {"id": "7", "name": "Utilities", "allocated": 320, "spent": 275},
    {"id": "8", "name": "Internet & Phone", "allocated": 180, "spent": 160},
    {"id": "9", "name": "Insurance", "allocated": 420, "spent": 390},
    {"id": "10", "name": "Healthcare", "allocated": 250, "spent": 110},
    {"id": "11", "name": "Subscriptions", "allocated": 95, "spent": 88},
    {"id": "12", "name": "Personal Care", "allocated": 120, "spent": 74},
    {"id": "13", "name": "Clothing", "allocated": 150, "spent": 60},
    {"id": "14", "name": "Gifts & Giving", "allocated": 100, "spent": 45},
    {"id": "15", "name": "Travel", "allocated": 300, "spent": 210},
    {"id": "16", "name": "Miscellaneous", "allocated": 90, "spent": 32},
]

SUMMARY_CARD = {
    "status": "On Track",
    "kicker": "Monthly Health",
    "meta": "Spending 68% of allocation",
}

TRANSACTIONS = [
    {
        "id": "1",
        "name": "Grocery run",
        "account": "Checking",
        "amount": -82.55,
        "date": "Apr 17",
    },
    {
        "id": "2",
        "name": "Rent",
        "account": "Checking",
        "amount": -1450.00,
        "date": "Apr 1",
    },
    {
        "id": "3",
        "name": "Gym membership",
        "account": "Credit",
        "amount": -45.00,
        "date": "Apr 12",
    },
    {
        "id": "4",
        "note": "RE",
        "name": "Paycheck",
        "account": "Checking",
        "amount": 2800.00,
        "date": "Apr 15",
    },
]

ACCOUNTS = [
    {"name": "Checking", "balance": 1850.24},
    {"name": "Savings", "balance": 4620.10},
    {"name": "Credit", "balance": -320.14},
]

TAGS = [
    {"name": "PLAIDX"},
    {"name": "Nike STORE CO LA"},
    {"name": "Checking OverDraft"},
]

SYNC_ACTIONS = [
    {"label": "Chase", "status": "Ready", "action": "Manual sync"},
    {"label": "Savings", "status": "Synced", "action": "Refresh in 24h"},
    {"label": "Brokerage", "status": "Needs login", "action": "Re-authenticate"},
]


def _base_context() -> dict:
    return {
        "budget_lines": BUDGET_LINES,
        "summary": SUMMARY_CARD,
        "transactions": TRANSACTIONS,
        "tags": TAGS,
        "accounts": ACCOUNTS,
        "sync_actions": SYNC_ACTIONS,
    }


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html", {"request": request, **_base_context()}
    )


@app.get("/budget-lines", response_class=HTMLResponse)
def budget_lines(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/budget_lines.html", {"request": request, **_base_context()}
    )


@app.get("/budgets/{id}", response_class=HTMLResponse)
def budget(id: int, request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/budget.html",
        {
            "request": request,
            "name": BUDGET_LINES[id - 1]["name"],
            "spent": BUDGET_LINES[id - 1]["spent"],
            "allocated": BUDGET_LINES[id - 1]["allocated"],
            "id": id,
            **_base_context(),
        },
    )


@app.post("/budgets/{id}", response_class=HTMLResponse)
def budget_update(
    id: int,
    request: Request,
    name: str | None = Form(None),
    allocated: float | None = Form(None),
) -> HTMLResponse:
    if name:
        BUDGET_LINES[id - 1]["name"] = name
    else:
        BUDGET_LINES[id - 1]["allocated"] = allocated

    return templates.TemplateResponse(
        "partials/budget.html",
        {
            "request": request,
            "name": BUDGET_LINES[id - 1]["name"],
            "spent": BUDGET_LINES[id - 1]["spent"],
            "allocated": BUDGET_LINES[id - 1]["allocated"],
            "id": id,
            **_base_context(),
        },
    )


@app.get("/budgets/{id}/edit", response_class=HTMLResponse)
def budget_edit(id: int, field: str, request: Request) -> HTMLResponse:
    value = None
    if field == "name":
        value = BUDGET_LINES[id - 1]["name"]
    else:
        value = BUDGET_LINES[id - 1]["allocated"]
    return templates.TemplateResponse(
        "partials/budget/edit.html",
        {
            "request": request,
            "id": id,
            "field": field,
            "value": value,
            **_base_context(),
        },
    )


@app.get("/budgets/{id}/transactions", response_class=HTMLResponse)
def budget_transactions(id: int, request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/budget/transactions.html",
        {"request": request, "id": id, **_base_context()},
    )


@app.get("/budgets/{id}/tags", response_class=HTMLResponse)
def budget_tags(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/budget/tags.html", {"request": request, **_base_context()}
    )


@app.get("/summary", response_class=HTMLResponse)
def summary_card(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/summary_card.html", {"request": request, **_base_context()}
    )


@app.get("/explorer", response_class=HTMLResponse)
def explorer_panel(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/explorer.html", {"request": request, **_base_context()}
    )


@app.get("/explorer/search", response_class=HTMLResponse)
def explorer_search(request: Request, q: str = "") -> HTMLResponse:
    query = q.lower().strip()
    filtered = (
        [
            tx
            for tx in TRANSACTIONS
            if query in tx["description"].lower()
            or query in tx["account"].lower()
            or query in tx["date"].lower()
        ]
        if query
        else TRANSACTIONS
    )
    context = {
        "request": request,
        **_base_context(),
        "transactions": filtered,
        "query": q,
    }
    return templates.TemplateResponse("partials/explorer.html", context)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True, workers=1)
