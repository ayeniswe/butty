# MARK: Imports
from datetime import datetime

from core.datasource.plaid_source import Plaid
from core.datastore.base import DataStore
from core.datastore.model import (
    PartialAccount,
    PartialBudget,
    PartialTransaction,
    TransactionDirection,
    TransactionSource,
    TransactionType,
    TransactionView,
)
from core.model import AppleTransaction
from core.utils import (
    build_fingerprint,
    cents_to_dollars,
    derive_direction,
    normalize,
)


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

    @staticmethod
    def __create_start_end_range(month: int, year: int, latest: bool = False):
        start = datetime(
            day=datetime.now().day if latest else 1, month=month, year=year
        )
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)

        return {"start": start, "end": end}

    @staticmethod
    def __build_transaction_fingerprint(
        name: str, amount: float, direction: TransactionDirection, date: datetime
    ):
        return build_fingerprint(name, str(amount), direction, date.isoformat())

    @staticmethod
    def __build_account_fingerprint(inst_id: str, name: str, subtype: float, mask: str):
        return build_fingerprint(inst_id, name, subtype, mask)

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
        return self.store.filter_budgets(
            **Service.__create_start_end_range(month, year)
        )

    def get_budget(self, id: int):
        budget = self.store.select_budget(id)
        return budget

    def get_transaction(self, id: int):
        return self.store.select_transaction(id)

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

    def get_budget_overview(self, month: int, year: int) -> dict:
        budgets = self.get_all_budgets(month, year)
        total_allocated = sum(budget.amount_allocated for budget in budgets)
        total_spent = sum(
            budget.amount_spent for budget in budgets if budget.amount_spent
        )
        return {
            "total_allocated": total_allocated,
            "total_spent": total_spent,
        }

    def refresh_budget_spent(self, budget_id: int) -> int:
        transactions = self.get_all_budget_transactions(budget_id)
        spent = sum(
            abs(transaction.amount)
            for transaction in transactions
            if transaction.direction == TransactionDirection.OUT
        )
        budget = self.get_budget(budget_id)
        self.store.update_budget(
            PartialBudget(
                id=budget.id,
                name=budget.name,
                amount_allocated=cents_to_dollars(budget.amount_allocated),
                amount_spent=spent,
                level=budget.level,
            )
        )
        return spent

    def _ensure_import_account(self, account_name: str) -> int:
        external_id = f"csv:{normalize(account_name)}"
        fingerprint = Service.__build_account_fingerprint(
            "CSV", account_name, TransactionType.DEPOSITORY, "0000"
        )
        account_id = self.store.account_exists_by_fingerprint(fingerprint)
        if account_id:
            return account_id

        return self.store.insert_account(
            PartialAccount(
                external_id=external_id,
                source=TransactionSource.PLAID,
                account_type=TransactionType.DEPOSITORY,
                name=account_name,
                balance=0,
                fingerprint=fingerprint,
            )
        )

    def import_transactions_from_csv(self, rows: list[dict[str, object]]) -> int:
        imported = 0
        budgets_by_month: dict[tuple[int, int], dict[str, int]] = {}

        for row in rows:
            occurred_at = row["occurred_at"]
            amount = row["amount"]
            account_name = row["account_name"]
            budget_name = row.get("budget_name", "")

            account_id = self._ensure_import_account(account_name)
            direction = (
                TransactionDirection.OUT if amount < 0 else TransactionDirection.IN
            )
            normalized_amount = abs(amount)
            transaction_id = self.store.insert_transaction(
                PartialTransaction(
                    row["description"],
                    normalized_amount,
                    direction,
                    account_id,
                    Service.__build_transaction_fingerprint(
                        row["description"],
                        normalized_amount,
                        direction,
                        occurred_at,
                    ),
                    occurred_at=occurred_at,
                )
            )
            imported += 1

            if not budget_name:
                continue

            key = (occurred_at.month, occurred_at.year)
            if key not in budgets_by_month:
                budgets = self.get_all_budgets(occurred_at.month, occurred_at.year)
                budgets_by_month[key] = {
                    budget.name.lower(): budget.id for budget in budgets
                }
            budget_id = budgets_by_month[key].get(budget_name.lower())
            if not budget_id:
                continue

            try:
                self.assign_transaction_to_budget(
                    budget_id, transaction_id, occurred_at.month, occurred_at.year
                )
            except ValueError:
                continue

        return imported

    # MARK: - Transactions

    def create_budget_transaction(
        self, budget_id: int, name: str, amount: float, account_id: str, date: str
    ):
        transaction_id = self.create_transaction(name, amount, account_id, date)
        self.store.insert_budget_transaction(budget_id, transaction_id)
        self.refresh_budget_spent(budget_id)

    def create_transaction(self, name: str, amount: float, account_id: str, date: str):
        amount = abs(amount)
        dir = TransactionDirection.OUT
        occurred_at = datetime.fromisoformat(date)
        return self.store.insert_transaction(
            PartialTransaction(
                name,
                amount,
                dir,
                account_id,
                Service.__build_transaction_fingerprint(name, amount, dir, occurred_at),
                occurred_at=occurred_at,
            )
        )

    def get_all_recent_transactions(self, month: int, year: int, latest: bool = False):
        return self.store.filter_transactions(
            **Service.__create_start_end_range(month, year, latest)
        )

    def get_all_transactions(self):
        return self.store.retrieve_transactions()

    def update_transaction_note(self, id: int, note: str):
        self.store.update_transaction_note(id, note)

    def unassign_transaction_to_budget(self, budget_id: int, transaction_id: int):
        if budget_id is None:
            budget_id = self.store.select_budget_id_for_transaction(transaction_id)

        if budget_id is None:
            return False

        self.store.delete_budget_transaction(budget_id, transaction_id)
        self.refresh_budget_spent(budget_id)
        return True

    def assign_transaction_to_budget(
        self, budget_id: int, transaction_id: int, month: int, year: int
    ):
        txn = self.get_transaction(transaction_id)
        occurred_at = txn.occurred_at
        if isinstance(occurred_at, str):
            occurred_at = datetime.fromisoformat(occurred_at)

        if occurred_at.month != month or occurred_at.year != year:
            raise ValueError("Transaction falls outside the selected month and year")

        self.store.insert_budget_transaction(budget_id, transaction_id)
        self.refresh_budget_spent(budget_id)

    def sync_all_transactions(self):
        self.__sync_plaid_transactions()

    # MARK: Transactions (Plaid Integration)

    def __sync_plaid_transactions(self):
        # NOTE
        # Any APPLE CARDS will not be processed here but rather
        # elsewhere in own domain

        for account in self.store.retrieve_plaid_accounts():
            p = self.store.select_plaid_account(account.id)
            acc = self.store.select_account_by_id(account.id)
            account_type = acc.account_type

            for transaction in self.plaid_client.retrieve_transactions(p.token):
                # Depends on enrichment and not guranteed but ideal
                merchant_name = transaction.merchant_name
                name = merchant_name if merchant_name else transaction.name

                amount = transaction.amount
                date = transaction.date
                direction = derive_direction(
                    amount, account_type == TransactionType.CREDIT
                )
                # NOTE
                # All transactions should be stored as cents
                self.store.insert_transaction(
                    PartialTransaction(
                        name,
                        amount,
                        direction,
                        account.id,
                        Service.__build_transaction_fingerprint(
                            name, amount, direction, date
                        ),
                        external_id=transaction.transaction_id,
                        occurred_at=date,
                    )
                )

    # MARK: Transactions (Apple Card Integration)

    def sync_apple_transactions(self, transactions: list[AppleTransaction]):
        # NOTE
        # All Apple transactions are expected to be credit from
        # Apple Card

        if transactions:
            # Must use first trans to get account since no
            # easy way to get accounts

            transaction = transactions[0]
            GENERIC_NAME = "Apple Card"
            fingerprint = Service.__build_account_fingerprint(
                GENERIC_NAME, GENERIC_NAME, TransactionType.CREDIT, 0
            )
            account_id = self.store.account_exists_by_fingerprint(fingerprint)

            if not account_id:
                account_id = self.store.insert_account(
                    PartialAccount(
                        transaction.account_id,
                        TransactionSource.APPLE,
                        TransactionType.CREDIT,
                        GENERIC_NAME,
                        0,  # TODO add the correct balance
                        fingerprint,
                    )
                )
            for transaction in transactions:
                # NOTE
                # All transactions should be stored as cents
                self.store.insert_transaction(
                    PartialTransaction(
                        transaction.name,
                        transaction.amount,
                        transaction.direction,
                        account_id,
                        Service.__build_transaction_fingerprint(
                            transaction.name,
                            transaction.amount,
                            transaction.direction,
                            transaction.date,
                        ),
                        external_id=transaction.id,
                        occurred_at=transaction.date,
                    )
                )

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

    def get_plaid_token(self):
        return self.plaid_client.create_link()

    # MARK: - Accounts (Plaid Integration)

    def create_accounts_by_plaid(
        self,
        public_token: str,
    ):
        access_token = self.plaid_client.add_financial_item(public_token)
        accounts = self.plaid_client.retrieve_accounts(access_token)

        PLAID_ACCOUNT_TYPE_MAP = {
            "credit": TransactionType.CREDIT,
            "depository": TransactionType.DEPOSITORY,
            "investment": TransactionType.INVESTMENT,
            "loan": TransactionType.LOAN,
        }

        new_accounts_data: list[dict] = []

        for account in accounts:
            fingerprint = account.fingerprint

            # Skip accounts that already exist (stable identity)
            if self.store.account_exists_by_fingerprint(fingerprint):
                continue

            new_accounts_data.append(
                {
                    "external_id": account.account_id,
                    "source": TransactionSource.PLAID,
                    "account_type": PLAID_ACCOUNT_TYPE_MAP.get(account.type),
                    "name": account.name,
                    "balance": account.balance,
                    "fingerprint": fingerprint,
                }
            )

        # 🚫 No new accounts discovered → do NOT persist access token
        if not new_accounts_data:
            return

        # ✅ At least one new account → now persist access token
        plaid_id = self.store.insert_plaid_account(access_token)

        for data in new_accounts_data:
            data["plaid_id"] = plaid_id
            self.store.insert_account(PartialAccount(**data))
