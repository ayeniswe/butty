from typing import List
import dotenv
import uvicorn
from fastapi import Body, Depends, FastAPI
from fastapi.responses import HTMLResponse
from fastapi.concurrency import asynccontextmanager
from datasource.plaid_source import Plaid
from datastore.db import Sqlite3
from datastore.model import PartialAccount, PartialTransaction, TransactionSource, TransactionType
from model import AppleTransaction, PlaidExchangeRequest
from utils import dollars_to_cents, derive_direction


@asynccontextmanager
async def startup(app: FastAPI):
    app.state.plaid_client = Plaid()
    app.state.datastore = Sqlite3("butty.sqlite")
    yield


app = FastAPI(lifespan=startup)


def get_plaid() -> Plaid:
    return app.state.plaid_client


def get_datastore() -> Sqlite3:
    return app.state.datastore


@app.get("/plaid/link", response_class=HTMLResponse)
def plaid_link_page(plaid: Plaid = Depends(get_plaid), ):
    link_token = plaid.create_link()

    return f"""
<!DOCTYPE html>
<html>
<head>
  <title>Link Bank</title>
  <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
</head>
<body>
  <script>
    const handler = Plaid.create({{
      token: "{link_token}",
      onSuccess: (public_token) => {{
        fetch("/plaid/exchange", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            public_token
          }})
        }}).then(() => {{
          alert("Account linked successfully");
        }});
      }}
    }});

    window.addEventListener("load", () => {{
      handler.open();
    }});
  </script>
</body>
</html>
"""


@app.post("/plaid/exchange")
def plaid_exchange(payload: PlaidExchangeRequest,
                   plaid: Plaid = Depends(get_plaid),
                   datastore: Sqlite3 = Depends(get_datastore)):
    access_token = plaid.add_financial_item(payload.public_token)
    plaid_id = datastore.insert_plaid_account(access_token)
    for account in plaid.get_accounts(access_token):
        PLAID_ACCOUNT_TYPE_MAP = {
            "credit": TransactionType.CREDIT,
            "depository": TransactionType.DEPOSITORY,
            "investment": TransactionType.INVESTMENT,
            "loan": TransactionType.LOAN,
        }
        datastore.insert_account(
            PartialAccount(account.account_id, TransactionSource.PLAID,
                           PLAID_ACCOUNT_TYPE_MAP.get(account.type.value),
                           account.name, plaid_id))


@app.get("/transactions/sync/plaid")
def sync_plaid_transactions(plaid: Plaid = Depends(get_plaid),
                            datastore: Sqlite3 = Depends(get_datastore)):
    # NOTE
    # Any APPLE CARDS will not be processed here but rather
    # elsewhere in own domain

    for account in datastore.get_plaid_accounts():
        p = datastore.select_plaid_account(account.id)
        for transaction in plaid.get_transactions(p.token):
            # Depends on enrichment and not guranteed but ideal
            merchant_name = transaction.merchant_name
            name = merchant_name if merchant_name else transaction.name

            amount = transaction.amount
            account_id = transaction.account_id
            is_credit = datastore.select_account_by_ext_id(
                account_id).account_type == TransactionType.CREDIT
            direction = derive_direction(amount, is_credit)
            # NOTE
            # All transactions should be stored as cents
            datastore.insert_transaction(
                PartialTransaction(name,
                                   dollars_to_cents(amount),
                                   direction,
                                   account_id,
                                   external_id=transaction.transaction_id,
                                   occurred_at=transaction.date))


@app.post("/transactions/sync/apple")
def sync_apple_transactions(payload: List[AppleTransaction] = Body(...),
                            datastore: Sqlite3 = Depends(get_datastore)):
    # NOTE
    # All Apple transactions are expected to be credit from
    # Apple Card

    if payload:
        # Must use first trans to get account since no
        # easy way to get accounts
        transaction = payload[0]
        account_id = datastore.insert_account(
            PartialAccount(transaction.account_id, TransactionSource.APPLE,
                           TransactionType.CREDIT, "Apple Card"))
        for transaction in payload:
            # NOTE
            # All transactions should be stored as cents
            datastore.insert_transaction(
                PartialTransaction(transaction.name,
                                   dollars_to_cents(transaction.amount),
                                   transaction.direction,
                                   account_id,
                                   external_id=transaction.id,
                                   occurred_at=transaction.date))


if __name__ == "__main__":
    dotenv.load_dotenv()
    uvicorn.run("server:app",
                host="0.0.0.0",
                port=8000,
                reload=True,
                workers=1)
