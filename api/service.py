# MARK: Imports
from datetime import datetime

from api.datasource.plaid_source import Plaid
from api.datastore.base import DataStore
from api.datastore.model import (
    PartialAccount,
    PartialBudget,
    PartialTransaction,
    TransactionDirection,
    TransactionSource,
    TransactionType,
    TransactionView,
)
from api.model import AppleTransaction, PlaidExchangeRequest
from api.utils import cents_to_dollars, derive_direction, dollars_to_cents


# MARK: Service Layer
class Service:
    def __init__(self, store: DataStore):
        self.store = store
        self.plaid_client = Plaid()

        self.summary_card = {
            "status": "On Track",
            "kicker": "Monthly Health",
            "meta": "Spending 68% of allocation",
        }
        self.sync_actions = [
            {"label": "Chase", "status": "Ready", "action": "Manual sync"},
            {"label": "Savings", "status": "Synced", "action": "Refresh in 24h"},
            {
                "label": "Brokerage",
                "status": "Needs login",
                "action": "Re-authenticate",
            },
        ]

    # MARK: - Budget Management

    def create_budget(self, name: str, allocated: float):
        self.store.insert_budget(name, allocated)

    def create_budget_from_copy(
        self, pre_month: int, pre_year: int, month: int, year: int
    ):
        past_budgets = self.get_all_budgets(pre_month, pre_year)
        current_budgets = self.get_all_budgets(month, year)
        existing_names = {b.name for b in current_budgets}

        for budget in past_budgets:
            if budget.name not in existing_names:
                self.store.insert_budget(
                    budget.name,
                    cents_to_dollars(budget.amount_allocated),
                    datetime(year=year, month=month, day=1),
                )

    def delete_budget(self, id: int):
        self.store.delete_budget(id)

    def get_all_budgets(self, month: int, year: int):
        start = datetime(day=1, month=month, year=year)

        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)

        return self.store.filter_budgets(start, end)

    def get_budget(self, id: int):
        budget = self.store.select_budget(id)
        return budget

    def edit_budget_name(self, id: int, name: str):
        budget = self.store.select_budget(id)
        self.store.update_budget(
            PartialBudget(
                id=budget.id,
                name=name,
                amount_allocated=cents_to_dollars(budget.amount_allocated),
                amount_spent=budget.amount_spent,
                level=budget.level,
            )
        )

    def edit_budget_allocated(self, id: int, allocated: float):
        budget = self.store.select_budget(id)
        self.store.update_budget(
            PartialBudget(
                id=budget.id,
                name=budget.name,
                amount_allocated=allocated,
                amount_spent=budget.amount_spent,
                level=budget.level,
            )
        )

    def get_all_budget_transactions(self, budget_id: int) -> list[TransactionView]:
        return self.store.retrieve_budget_transactions(budget_id)

    # MARK: - Transactions

    def create_budget_transaction(
        self, budget_id: int, name: str, amount: float, account_id: str, date: str
    ):
        transaction_id = self.create_transaction(name, amount, account_id, date)
        self.store.insert_budget_transaction(budget_id, transaction_id)

    def create_transaction(self, name: str, amount: float, account_id: str, date: str):
        return self.store.insert_transaction(
            PartialTransaction(
                name,
                abs(amount),
                TransactionDirection.OUT,
                account_id,
                occurred_at=date,
            )
        )

    def update_transaction_note(self, id: int, note: str):
        self.store.update_transaction_note(id, note)

    def unassign_transaction_to_budget(self, budget_id: int, transaction_id: int):
        self.store.delete_budget_transaction(budget_id, transaction_id)

    # MARK: - Tags

    def create_tag(self, name: str):
        return self.store.insert_tag(name)

    def delete_tag(self, id: int):
        self.tags = [tag for tag in self.tags if tag["id"] != str(id)]

    def search_tags(self, query: str) -> list[dict[str, str]]:
        return [
            tag
            for tag in self.store.retrieve_tags()
            if query.lower() in tag.name.lower()
        ]

    def get_all_budget_tags(self, budget_id: int) -> list[dict[str, str]]:
        return self.store.retrieve_budget_tags(budget_id)

    def assign_tag_to_budget(self, budget_id: int, tag_id: int):
        self.store.insert_budget_tag(budget_id, tag_id)

    def unassign_tag_from_budget(self, budget_id: int, tag_id: int):
        self.store.delete_budget_tag(budget_id, tag_id)

    # MARK: - Accounts

    def get_all_accounts(self):
        return self.store.retrieve_accounts()

    # MARK: - Plaid Integration

    def plaid_link_page(self):
        link_token = self.plaid_client.create_link()

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

    def plaid_exchange(
        self,
        request: PlaidExchangeRequest,
    ):
        access_token = self.plaid_client.add_financial_item(request.public_token)
        plaid_id = self.store.insert_plaid_account(access_token)
        for account in self.plaid_client.retrieve_accounts(access_token):
            PLAID_ACCOUNT_TYPE_MAP = {
                "credit": TransactionType.CREDIT,
                "depository": TransactionType.DEPOSITORY,
                "investment": TransactionType.INVESTMENT,
                "loan": TransactionType.LOAN,
            }
            self.store.insert_account(
                PartialAccount(
                    account.account_id,
                    TransactionSource.PLAID,
                    PLAID_ACCOUNT_TYPE_MAP.get(account.type.value),
                    account.name,
                    plaid_id,
                )
            )

    def sync_plaid_transactions(self):
        # NOTE
        # Any APPLE CARDS will not be processed here but rather
        # elsewhere in own domain

        for account in self.store.retrieve_plaid_accounts():
            p = self.store.select_plaid_account(account.id)
            for transaction in self.plaid_client.retrieve_transactions(p.token):
                # Depends on enrichment and not guranteed but ideal
                merchant_name = transaction.merchant_name
                name = merchant_name if merchant_name else transaction.name

                amount = transaction.amount
                account_id = transaction.account_id
                is_credit = (
                    self.store.select_account_by_ext_id(account_id).account_type
                    == TransactionType.CREDIT
                )
                direction = derive_direction(amount, is_credit)
                # NOTE
                # All transactions should be stored as cents
                self.store.insert_transaction(
                    PartialTransaction(
                        name,
                        dollars_to_cents(amount),
                        direction,
                        account_id,
                        external_id=transaction.transaction_id,
                        occurred_at=transaction.date,
                    )
                )

    # MARK: - Apple Card Integration

    def sync_apple_transactions(self, transactions: list[AppleTransaction]):
        # NOTE
        # All Apple transactions are expected to be credit from
        # Apple Card

        if transactions:
            # Must use first trans to get account since no
            # easy way to get accounts
            transaction = transactions[0]
            account_id = self.store.insert_account(
                PartialAccount(
                    transaction.account_id,
                    TransactionSource.APPLE,
                    TransactionType.CREDIT,
                    "Apple Card",
                )
            )
            for transaction in transactions:
                # NOTE
                # All transactions should be stored as cents
                self.store.insert_transaction(
                    PartialTransaction(
                        transaction.name,
                        dollars_to_cents(transaction.amount),
                        transaction.direction,
                        account_id,
                        external_id=transaction.id,
                        occurred_at=transaction.date,
                    )
                )
