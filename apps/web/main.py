# MARK: Imports
from calendar import month_name
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api.datastore.db import Sqlite3
from api.service import Service
from api.utils import cents_to_dollars

# MARK: App Setup & Lifespan


@asynccontextmanager
async def startup(app: FastAPI):
    app.state.service = Service(Sqlite3("butty.sqlite"))
    yield


app = FastAPI(title="Budget Dashboard", lifespan=startup)

# Routers
root_router = APIRouter()
budget_router = APIRouter(prefix="/budgets")
tag_router = APIRouter(prefix="/tags")


def get_service():
    yield app.state.service


templates = Jinja2Templates(directory="apps/web/templates")
app.mount("/static", StaticFiles(directory="apps/web/static"), name="static")


# MARK: Shared Helpers


def _base_context(service: Service) -> dict:
    return {
        "summary": service.summary_card,
        "sync_actions": service.sync_actions,
    }


def _month_context(month: int | None = None, year: int | None = None) -> dict:
    now = datetime.now()

    base_year = year if year is not None else now.year
    base_month = month if month is not None else now.month

    # Normalize month overflow/underflow (e.g. 0, 13, -1)
    year_offset, normalized_month = divmod(base_month - 1, 12)
    current_year = base_year + year_offset
    current_month = normalized_month + 1

    current = datetime(year=current_year, month=current_month, day=1)

    return {
        "current_month_name": month_name[current.month][0:3],
        "current_month": current.month,
        "prev_year": current.year - 1 if current.month == 1 else current.year,
        "year": current.year,
        "now_year": now.year,
        "now_month": now.month,
        "readonly": (current_year == now.year and current.month < now.month)
        or (current_year < now.year),
        "next_month": current.month + 1,
        "prev_month": current.month - 1,
    }


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
    request: Request, service: Annotated[Service, Depends(get_service)]
) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/explorer.html", {"request": request, **_base_context(service)}
    )


@root_router.get("/explorer/search", response_class=HTMLResponse)
def explorer_search(
    request: Request, service: Annotated[Service, Depends(get_service)], q: str = ""
) -> HTMLResponse:
    query = q.lower().strip()
    filtered = (
        [
            tx
            for tx in service.transactions
            if query in tx["description"].lower()
            or query in tx["account"].lower()
            or query in tx["date"].lower()
        ]
        if query
        else service.transactions
    )
    context = {
        "request": request,
        **_base_context(service),
        "transactions": filtered,
        "query": q,
    }
    return templates.TemplateResponse("partials/explorer.html", context)


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


# MARK: Router Registration


app.include_router(root_router)
app.include_router(budget_router)
app.include_router(tag_router)


# MARK: Dev Entrypoint


if __name__ == "__main__":
    import dotenv

    dotenv.load_dotenv()
    uvicorn.run("apps.web.main:app", host="0.0.0.0", port=8001, reload=True, workers=1)
