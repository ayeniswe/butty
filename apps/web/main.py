from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api.datastore.db import Sqlite3
from api.service import Service


@asynccontextmanager
async def startup(app: FastAPI):
    app.state.service = Service(Sqlite3)
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


def _base_context(service: Service) -> dict:
    return {
        "budget_lines": service.budget_lines,
        "summary": service.summary_card,
        "transactions": service.transactions,
        "tags": service.tags,
        "accounts": service.accounts,
        "sync_actions": service.sync_actions,
    }


# MARK: === Root ===


@root_router.get("/", response_class=HTMLResponse)
def read_root(
    request: Request, service: Annotated[Service, Depends(get_service)]
) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html", {"request": request, **_base_context(service)}
    )


@root_router.get("/budget-lines", response_class=HTMLResponse)
def budget_lines(
    request: Request, service: Annotated[Service, Depends(get_service)]
) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/budget_lines.html", {"request": request, **_base_context(service)}
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


# MARK: - === Budgets ===


@budget_router.get("/{id}", response_class=HTMLResponse)
def budget(
    id: int, request: Request, service: Annotated[Service, Depends(get_service)]
) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/budget.html",
        {
            "request": request,
            "name": service.budget_lines[id - 1]["name"],
            "spent": service.budget_lines[id - 1]["spent"],
            "allocated": service.budget_lines[id - 1]["allocated"],
            "id": id,
            **_base_context(service),
        },
    )


@budget_router.post("/{id}", response_class=HTMLResponse)
def budget_update(
    id: int,
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    name: str | None = Form(None),
    allocated: float | None = Form(None),
) -> HTMLResponse:
    if name:
        service.budget_lines[id - 1]["name"] = name
    else:
        service.budget_lines[id - 1]["allocated"] = allocated

    return templates.TemplateResponse(
        "partials/budget.html",
        {
            "request": request,
            "name": service.budget_lines[id - 1]["name"],
            "spent": service.budget_lines[id - 1]["spent"],
            "allocated": service.budget_lines[id - 1]["allocated"],
            "id": id,
            **_base_context(service),
        },
    )


@budget_router.post("", response_class=HTMLResponse)
def budget_create(
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    name: str = Form(...),
    allocated: float = Form(...),
) -> HTMLResponse:
    service.create_budget(name, allocated)

    return templates.TemplateResponse(
        "partials/budget_lines.html", {"request": request, **_base_context(service)}
    )


@budget_router.delete("/{id}", response_class=HTMLResponse)
def budget_delete(
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    id: int,
) -> HTMLResponse:
    service.delete_budget(id)

    return templates.TemplateResponse(
        "partials/budget_lines.html", {"request": request, **_base_context(service)}
    )


@budget_router.get("/{id}/edit", response_class=HTMLResponse)
def budget_edit(
    id: int,
    field: str,
    request: Request,
    service: Annotated[Service, Depends(get_service)],
) -> HTMLResponse:
    value = None
    if field == "name":
        value = service.budget_lines[id - 1]["name"]
    else:
        value = service.budget_lines[id - 1]["allocated"]
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


@budget_router.get("/{id}/transactions", response_class=HTMLResponse)
def budget_transactions(
    id: int, request: Request, service: Annotated[Service, Depends(get_service)]
) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/budget/transactions.html",
        {"request": request, "id": id, **_base_context(service)},
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
    service.create_transaction(name, amount, account_id, date)

    return templates.TemplateResponse(
        "partials/budget/transactions.html",
        {"request": request, "id": id, **_base_context(service)},
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
        {"request": request, "id": id, **_base_context(service)},
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


@budget_router.get("/{id}/tags", response_class=HTMLResponse)
def budget_tags(
    request: Request, id: int, service: Annotated[Service, Depends(get_service)]
) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/budget/tags.html",
        {"request": request, "id": id, **_base_context(service)},
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
        {"request": request, "id": id, **_base_context(service)},
    )


@budget_router.delete("/{id}/tags/{tag_id}", response_class=HTMLResponse)
def budget_tag_delete(
    id: int,
    tag_id: int,
    request: Request,
    service: Annotated[Service, Depends(get_service)],
) -> HTMLResponse:
    service.unassign_tag_to_budget(id, tag_id)

    return templates.TemplateResponse(
        "partials/budget/tags.html",
        {"request": request, "id": id, **_base_context(service)},
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


# MARK: === Tags ===


@tag_router.delete("/{id}", response_class=HTMLResponse)
def tag_delete(
    request: Request,
    service: Annotated[Service, Depends(get_service)],
    id: int,
) -> HTMLResponse:
    service.delete_tag(id)

    return templates.TemplateResponse(
        "partials/budget_lines.html", {"request": request, **_base_context(service)}
    )


app.include_router(root_router)
app.include_router(budget_router)
app.include_router(tag_router)

#  TO USE FOR LINKING ACCOUNTS
# @app.get("/plaid/link", response_class=HTMLResponse)
# def plaid_link_page(plaid: Annotated[Plaid, Depends(get_plaid)], ):

# @app.post("/plaid/exchange")
# def plaid_exchange(
#     payload: PlaidExchangeRequest,
#     plaid: Annotated[Plaid, Depends(get_plaid)],
#     datastore: Annotated[Sqlite3, Depends(get_datastore)],
# ):

# @app.post("/transactions/sync/plaid")
# def sync_plaid_transactions(
#     plaid: Annotated[Plaid, Depends(get_plaid)],
#     datastore: Annotated[Sqlite3, Depends(get_datastore)],
# ):

# @app.post("/transactions/sync/apple")
# def sync_apple_transactions(
#     payload: Annotated[list[AppleTransaction], Body(...)],
#     datastore: Annotated[Sqlite3, Depends(get_datastore)],
# ):

if __name__ == "__main__":
    import dotenv

    dotenv.load_dotenv()
    uvicorn.run("apps.web.main:app", host="0.0.0.0", port=8001, reload=True, workers=1)
