from api.datasource.plaid_source import Plaid
from api.datastore.base import DataStore
from api.datastore.model import (
    PartialAccount,
    PartialTransaction,
    TransactionSource,
    TransactionType,
)
from api.model import AppleTransaction, PlaidExchangeRequest
from api.utils import derive_direction, dollars_to_cents


class Service:
    def __init__(self, store: DataStore):
        self.store = store
        self.plaid_client = Plaid()
        self.budget_lines: list[dict[str, float]] = [
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

        self.summary_card = {
            "status": "On Track",
            "kicker": "Monthly Health",
            "meta": "Spending 68% of allocation",
        }

        self.transactions = [
            {
                "id": "1",
                "name": "Grocery run",
                "account_id": "1",
                "account": "Checking",
                "amount": -82.55,
                "date": "Apr 17",
            },
            {
                "id": "2",
                "name": "Rent",
                "account_id": "1",
                "account": "Checking",
                "amount": -1450.00,
                "date": "Apr 1",
            },
            {
                "id": "3",
                "name": "Gym membership",
                "account_id": "3",
                "account": "Credit",
                "amount": -45.00,
                "date": "Apr 12",
            },
            {
                "id": "4",
                "note": "RE",
                "name": "Paycheck",
                "account_id": "1",
                "account": "Checking",
                "amount": 2800.00,
                "date": "Apr 15",
            },
        ]

        self.accounts = [
            {"name": "Checking", "balance": 1850.24, "id": "1"},
            {
                "name": "Savings",
                "balance": 4620.10,
                "id": "2",
            },
            {"name": "Credit", "balance": -320.14, "id": "3"},
        ]

        self.tags = [
            {"name": "PLAIDX", "id": "1"},
            {"name": "Nike STORE CO LA", "id": "2"},
            {"name": "Checking OverDraft", "id": "3"},
        ]

        self.sync_actions = [
            {"label": "Chase", "status": "Ready", "action": "Manual sync"},
            {"label": "Savings", "status": "Synced", "action": "Refresh in 24h"},
            {
                "label": "Brokerage",
                "status": "Needs login",
                "action": "Re-authenticate",
            },
        ]

    def create_budget(self, name: str, allocated: float):
        self.budget_lines.append(
            {
                "id": str(len(self.budget_lines) + 1),
                "name": name,
                "allocated": allocated,
                "spent": 0.0,
            }
        )

    def create_transaction(self, name: str, amount: float, account_id: str, date: str):
        print(account_id)
        self.transactions.append(
            {
                "id": str(len(self.transactions) + 1),
                "name": name,
                "account": self.accounts[int(account_id) - 1]["name"],
                "account_id": account_id,
                "amount": amount,
                "date": date,
            }
        )

    def update_transaction_note(self, id: int, note: str):
        for transaction in self.transactions:
            if transaction["id"] == str(id):
                transaction["note"] = note
                break

    def create_tag(self, name: str):
        id = len(self.tags) + 1
        self.tags.append({"name": name, "id": str(id)})
        return id

    def delete_budget(self, id: int):
        self.budget_lines = [
            budget for budget in self.budget_lines if budget["id"] != str(id)
        ]

    def unassign_transaction_to_budget(self, budget_id: int, transaction_id: int):
        print(f"Unassigned transaction {transaction_id} to budget {budget_id}")

    def unassign_tag_to_budget(self, budget_id: int, tag_id: int):
        print(f"Unassigned tag {tag_id} to budget {budget_id}")

    def delete_transaction(self, id: int):
        self.transactions = [
            transaction
            for transaction in self.transactions
            if transaction["id"] != str(id)
        ]

    def delete_tag(self, id: int):
        self.tags = [tag for tag in self.tags if tag["id"] != str(id)]

    def search_tags(self, query: str) -> list[dict[str, str]]:
        return [tag for tag in self.tags if query.lower() in tag["name"].lower()]

    def assign_tag_to_budget(self, budget_id: int, tag_id: int):
        print(f"Assigned tag {tag_id} to budget {budget_id}")

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
        for account in self.plaid_client.get_accounts(access_token):
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

        for account in self.store.get_plaid_accounts():
            p = self.store.select_plaid_account(account.id)
            for transaction in self.plaid_client.get_transactions(p.token):
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
