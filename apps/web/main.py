# MARK: Imports
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.datastore.db import Sqlite3
from core.model import AppleTransaction
from core.service import Service
from core.utils import cents_to_dollars, derive_month_context

# MARK: App Setup & Lifespan


@asynccontextmanager
async def startup(app: FastAPI):
    app.state.service = Service(Sqlite3("butty.sqlite"))
    yield


app = FastAPI(title="Budget Dashboard", lifespan=startup)

# Routers
root_router = APIRouter()
budget_router = APIRouter(prefix="/budgets")
link_router = APIRouter(prefix="/link")
account_router = APIRouter(prefix="/accounts")
transactions_router = APIRouter(prefix="/transactions")
tag_router = APIRouter(prefix="/tags")


def get_service():
    yield app.state.service


templates = Jinja2Templates(directory="apps/web/templates")
app.mount("/static", StaticFiles(directory="apps/web/static"), name="static")


# MARK: Shared Helpers


def _base_context(service: Service) -> dict:
    return {"summary": service.summary_card}


def _month_context(month: int | None = None, year: int | None = None) -> dict:
    return derive_month_context(month, year)


def _activity_context(
    service: Annotated[Service, Depends(get_service)],
    month: int | None = None,
    year: int | None = None,
) -> dict:
    mth_ctx = _month_context(month, year)
    recent_transactions = service.get_all_recent_transactions(
        mth_ctx["current_month"], mth_ctx["year"], True
    )
    transactions = service.get_all_transactions()
    accounts = service.get_all_accounts()
    return {
        "recent_transactions": recent_transactions,
        "transactions": transactions,
        "accounts": accounts,
        "budgets": service.get_all_budgets(mth_ctx["current_month"], mth_ctx["year"]),
        **mth_ctx,
    }


def _explorer_response(
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    month: int | None = None,
    year: int | None = None,
):
    return templates.TemplateResponse(
        "partials/explorer/index.html",
        {
            "request": request,
            **_activity_context(service, month, year),
            **_base_context(service),
        },
    )


# MARK: Root Routes


@root_router.get("/", response_class=HTMLResponse)
def read_root(
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    month: int | None = Query(None),
    year: int | None = Query(None),
) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {"request": request, **_month_context(month, year), **_base_context(service)},
    )


@root_router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    month: int | None = Query(None),
    year: int | None = Query(None),
) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/dashboard.html",
        {"request": request, **_month_context(month, year), **_base_context(service)},
    )


@root_router.get("/summary", response_class=HTMLResponse)
def summary_card(
    request: Request, service: Annotated[Service, Depends(get_service)]
) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/summary_card.html", {"request": request, **_base_context(service)}
    )


@root_router.get("/explorer", response_class=HTMLResponse)
def explorer_panel(
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    month: int | None = Query(None),
    year: int | None = Query(None),
) -> HTMLResponse:
    return _explorer_response(request, service, month, year)


@root_router.get("/explorer/search", response_class=HTMLResponse)
def explorer_search(
    request: Request, service: Annotated[Service, Depends(get_service)], query: str = ""
) -> HTMLResponse:
    query = query.lower().strip()

    # TODO apply better perf
    # Raw and dirty but obviously better way
    transactions = service.get_all_transactions()
    filtered = (
        [
            tx
            for tx in transactions
            if query in tx.name.lower()
            or query in tx.account_name.lower()
            or query in tx.occurred_at
            or tx.budget_name
            and query in tx.budget_name.lower()
        ]
        if query
        else transactions
    )

    context = {
        "request": request,
        "transactions": filtered,
        "query": query,
        **_base_context(service),
    }
    return templates.TemplateResponse("partials/explorer/search.html", context)


# MARK: - Budget CRUD


@budget_router.get("", response_class=HTMLResponse)
def budget_lines(
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    month: int,
    year: int | None = Query(None),
) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/budget_lines.html",
        {
            "request": request,
            "budgets": service.get_all_budgets(
                month, datetime.now().year if not year else year
            ),
            **_month_context(month, year),
        },
    )


@budget_router.post("", response_class=HTMLResponse)
def budget_create(
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    name: str = Form(...),
    allocated: float | None = Form(None),
    month: int = Query(...),
    year: int | None = Query(None),
) -> HTMLResponse:
    service.create_budget(name, allocated if allocated is not None else 0.0)

    return templates.TemplateResponse(
        "partials/budget_lines.html",
        {
            "request": request,
            "budgets": service.get_all_budgets(
                month, datetime.now().year if not year else year
            ),
            **_month_context(month, year),
        },
    )


@budget_router.post("/copy", response_class=HTMLResponse)
def budget_copy(
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    month: int = Query(...),
    year: int | None = Query(None),
) -> HTMLResponse:
    mth_ctx = _month_context(month, year)
    service.create_budget_from_copy(
        12 if mth_ctx["prev_month"] == 0 else mth_ctx["prev_month"],
        mth_ctx["prev_year"],
        month,
        year,
    )

    return templates.TemplateResponse(
        "partials/budget_lines.html",
        {
            "request": request,
            "budgets": service.get_all_budgets(
                month, datetime.now().year if not year else year
            ),
            **mth_ctx,
        },
    )


@budget_router.get("/{id}", response_class=HTMLResponse)
def budget(
    id: int,
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    month: int = Query(...),
    year: int | None = Query(None),
) -> HTMLResponse:
    budget = service.get_budget(id)
    return templates.TemplateResponse(
        "partials/budget/index.html",
        {
            "request": request,
            "name": budget.name,
            "spent": budget.amount_spent,
            "allocated": budget.amount_allocated,
            "id": budget.id,
            **_month_context(month, year),
            **_base_context(service),
        },
    )


@budget_router.patch("/{id}", response_class=HTMLResponse)
def budget_update(
    id: int,
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    name: str | None = Form(None),
    allocated: float | None = Form(None),
    month: int = Query(None),
    year: int | None = Form(None),
) -> HTMLResponse:
    if name:
        service.edit_budget_name(id, name)
    else:
        service.edit_budget_allocated(id, allocated)

    budget = service.get_budget(id)

    return templates.TemplateResponse(
        "partials/budget/index.html",
        {
            "request": request,
            "name": budget.name,
            "spent": budget.amount_spent,
            "allocated": budget.amount_allocated,
            "id": budget.id,
            **_month_context(month, year),
            **_base_context(service),
        },
    )


@budget_router.delete("/{id}", response_class=HTMLResponse)
def budget_delete(
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    id: int,
    month: int = Query(...),
    year: int | None = Query(None),
) -> HTMLResponse:
    service.delete_budget(id)

    return templates.TemplateResponse(
        "partials/budget_lines.html",
        {
            "request": request,
            "budgets": service.get_all_budgets(
                month, datetime.now().year if not year else year
            ),
            **_month_context(month, year),
        },
    )


@budget_router.get("/{id}/edit", response_class=HTMLResponse)
def budget_edit(
    id: int,
    field: str,
    request: Request,
    service: Annotated[Service, Depends(get_service)],
) -> HTMLResponse:
    budget = service.get_budget(id)
    value = None
    if field == "name":
        value = budget.name
    else:
        value = cents_to_dollars(budget.amount_allocated)
    return templates.TemplateResponse(
        "partials/budget/edit.html",
        {
            "request": request,
            "id": id,
            "field": field,
            "value": value,
            **_base_context(service),
        },
    )


# MARK: - Budget Transactions


@budget_router.get("/{id}/transactions", response_class=HTMLResponse)
def budget_transactions(
    id: int,
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    month: int = Query(...),
    year: int | None = Query(None),
) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/budget/transactions.html",
        {
            "request": request,
            "id": id,
            "accounts": service.get_all_accounts(),
            "transactions": service.get_all_budget_transactions(id),
            **_month_context(month, year),
        },
    )


@budget_router.post("/{id}/transactions", response_class=HTMLResponse)
def create_budget_transaction(
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    id: int,
    name: str = Form(...),
    account_id: str = Form(...),
    amount: float = Form(...),
    date: str = Form(...),
) -> HTMLResponse:
    service.create_budget_transaction(id, name, amount, account_id, date)

    return templates.TemplateResponse(
        "partials/budget/transactions.html",
        {
            "request": request,
            "id": id,
            "accounts": service.get_all_accounts(),
            "transactions": service.get_all_budget_transactions(id),
        },
    )


@budget_router.post(
    "/{id}/transactions/{transaction_id}/note", response_class=HTMLResponse
)
def update_budget_transaction_note(
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    id: int,
    transaction_id: int,
    note: str | None = Form(None),
) -> HTMLResponse:
    if note is None:
        note = ""
    service.update_transaction_note(transaction_id, note)

    return templates.TemplateResponse(
        "partials/budget/transactions.html",
        {
            "request": request,
            "id": id,
            "transactions": service.get_all_budget_transactions(id),
        },
    )


@budget_router.delete(
    "/{id}/transactions/{transaction_id}", response_class=HTMLResponse
)
def budget_transaction_delete(
    id: int,
    transaction_id: int,
    request: Request,
    service: Annotated[Service, Depends(get_service)],
) -> HTMLResponse:
    service.unassign_transaction_to_budget(id, transaction_id)

    return templates.TemplateResponse(
        "partials/budget/transactions.html",
        {"request": request, "id": id, **_base_context(service)},
    )


# MARK: - Budget Tags


@budget_router.get("/{id}/tags", response_class=HTMLResponse)
def budget_tags(
    request: Request,
    id: int,
    service: Annotated[Service, Depends(get_service)],
    month: int = Query(...),
    year: int | None = Query(None),
) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/budget/tags.html",
        {
            "request": request,
            "id": id,
            "tags": service.get_all_budget_tags(id),
            **_month_context(month, year),
        },
    )


@budget_router.post("/{id}/tags", response_class=HTMLResponse)
def create_budget_tag(
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    id: int,
    name: str | None = Form(None),
    tag_id: int | None = Form(None),
) -> HTMLResponse:
    tag_id = tag_id if tag_id else service.create_tag(name)
    service.assign_tag_to_budget(id, tag_id)

    return templates.TemplateResponse(
        "partials/budget/tags.html",
        {"request": request, "id": id, "tags": service.get_all_budget_tags(id)},
    )


@budget_router.delete("/{id}/tags/{tag_id}", response_class=HTMLResponse)
def budget_tag_delete(
    id: int,
    tag_id: int,
    request: Request,
    service: Annotated[Service, Depends(get_service)],
) -> HTMLResponse:
    service.unassign_tag_from_budget(id, tag_id)

    return templates.TemplateResponse(
        "partials/budget/tags.html",
        {"request": request, "id": id, "tags": service.get_all_budget_tags(id)},
    )


@budget_router.get("/{id}/tags/search", response_class=HTMLResponse)
def tag_search(
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    id: int,
    query: str = Query(None),
) -> HTMLResponse:
    tags = service.search_tags(query) if query else []
    return templates.TemplateResponse(
        "partials/budget/tag/search.html",
        {"request": request, "tags": tags, "id": id, "query": query},
    )


# MARK: Transactions


@transactions_router.get("/context-menu/budgets", response_class=HTMLResponse)
def context_menu_budgets(
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    month: int | None = Query(None),
    year: int | None = Query(None),
) -> HTMLResponse:
    mth_ctx = _month_context(month, year)
    return templates.TemplateResponse(
        "partials/explorer/context_menu_budgets.html",
        {
            "request": request,
            "budgets": service.get_all_budgets(
                mth_ctx["current_month"], mth_ctx["year"]
            ),
            **mth_ctx,
        },
    )


@transactions_router.post("/note", response_class=HTMLResponse)
def transaction_note(
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    transaction_id: int = Form(...),
    note: str = Form(""),
    month: int = Form(...),
    year: int = Form(...),
) -> HTMLResponse:
    service.update_transaction_note(transaction_id, note)
    return _explorer_response(request, service, month, year)


@transactions_router.post("/budget", response_class=HTMLResponse)
def transaction_assign_budget(
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    transaction_id: int = Form(...),
    budget_id: int = Form(...),
    month: int = Form(...),
    year: int = Form(...),
) -> HTMLResponse:
    try:
        service.assign_transaction_to_budget(budget_id, transaction_id, month, year)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _explorer_response(request, service, month, year)


@transactions_router.delete("/budget", response_class=HTMLResponse)
def transaction_remove_budget(
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    transaction_id: int = Form(...),
    month: int = Form(...),
    year: int = Form(...),
) -> HTMLResponse:
    service.unassign_transaction_to_budget(None, transaction_id)
    return _explorer_response(request, service, month, year)


@transactions_router.get("/sync", response_class=HTMLResponse)
def sync_transactions(
    request: Request,
    service: Annotated[Service, Depends(get_service)],
) -> HTMLResponse:
    service.sync_all_transactions()
    return _explorer_response(request, service)


@transactions_router.post("/sync/apple", response_class=HTMLResponse)
def sync_transactions_apple_webhook(
    service: Annotated[Service, Depends(get_service)], payload: list[AppleTransaction]
):
    service.sync_apple_transactions(payload)


# MARK: Plaid


@link_router.get("", response_class=HTMLResponse)
def link_by_plaid(
    request: Request, service: Annotated[Service, Depends(get_service)]
) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/plaid_button.html",
        {"request": request, "link_token": service.get_plaid_token()},
    )


@account_router.post("/plaid", response_class=HTMLResponse)
def create_account_by_plaid(
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    public_token: str = Form(...),
) -> HTMLResponse:
    service.create_accounts_by_plaid(public_token)
    service.sync_all_transactions()
    return _explorer_response(request, service)


# MARK: Router Registration


app.include_router(root_router)
app.include_router(budget_router)
app.include_router(tag_router)
app.include_router(link_router)
app.include_router(account_router)
app.include_router(transactions_router)


# MARK: Dev Entrypoint


if __name__ == "__main__":
    import dotenv

    dotenv.load_dotenv()
    uvicorn.run("apps.web.main:app", host="0.0.0.0", port=8001, reload=True, workers=1)
