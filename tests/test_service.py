import datetime

import pytest

from core.datastore.model import (
    Account,
    Budget,
    PartialAccount,
    PartialBudget,
    PartialTransaction,
    PlaidAccount,
    Tag,
    Transaction,
    TransactionDirection,
    TransactionSource,
    TransactionType,
)
from core.model import AppleTransaction
from core.service import Service


class FakePlaid:
    def __init__(self):
        self.link_token_called = False

    def create_link(self):
        self.link_token_called = True
        return "link-token"

    def add_financial_item(self, public_token: str):
        return f"access-{public_token}"

    def retrieve_accounts(self, access_token: str):
        from core.datasource.model import PlaidAccountBase

        return [
            PlaidAccountBase("acc1", "Checking", "finger1", "depository", 1200),
            PlaidAccountBase("acc2", "Credit", "finger2", "credit", 800),
        ]

    def retrieve_transactions(self, access_token: str):
        class Txn:
            def __init__(self, name, merchant, amount, date, transaction_id):
                self.name = name
                self.merchant_name = merchant
                self.amount = amount
                self.date = date
                self.transaction_id = transaction_id

        now = datetime.datetime(2023, 1, 15)
        return [
            Txn("Merchant A", None, 2500, now, "t-1"),
            Txn("Merchant B", "Store B", -500, now, "t-2"),
        ]


class FakeStore:
    def __init__(self):
        self.budgets = []
        self.inserted_budgets = []
        self.transactions = []
        self.transaction_fingerprints: dict[str, int] = {}
        self.transaction_external_ids: dict[str, int] = {}
        self.force_insert_transaction_none = False
        self.inserted_budget_transactions = []
        self.transaction_note_updates = []
        self.budget_updates: list[PartialBudget] = []
        self.selected_budget_id: int | None = None
        self.deleted_budget_transactions = []
        self.plaid_accounts = [PlaidAccount(1, "token-1")]
        self.accounts_by_id = {
            1: Account(
                id=1,
                external_id="plaid-acc",
                account_type=TransactionType.CREDIT,
                source=TransactionSource.PLAID,
                name="Credit Card",
                balance=0,
                plaid_id=1,
            )
        }
        self.tag_assignments = []
        self.budget_tags = []
        self.plaid_inserted_token = None
        self.inserted_accounts: list[PartialAccount] = []
        self.tags = [{"id": "1"}, {"id": "2"}]

    def insert_budget(self, name, allocated, created_at=None):
        self.inserted_budgets.append((name, allocated, created_at))

    def filter_budgets(self, **kwargs):
        start = kwargs.get("start")
        end = kwargs.get("end")
        if start and end:
            return [
                b
                for b in self.budgets
                if getattr(b, "created_at", None) is None
                or (start <= b.created_at < end)
            ]
        return list(self.budgets)

    def select_budget(self, id: int):
        for budget in self.budgets:
            if budget.id == id:
                return budget
        raise IndexError("Budget not found")

    def delete_budget(self, id: int):
        self.deleted_budget = id

    def select_transaction(self, id: int):
        return self.transactions[id]

    def update_budget(self, partial: PartialBudget):
        self.budget_updates.append(partial)

    def retrieve_budget_transactions(self, budget_id: int):
        return [
            Transaction(
                id=1,
                name="Food",
                amount=1200,
                direction=TransactionDirection.OUT,
                occurred_at="2023-01-01",
                account_id=1,
                external_id=None,
                note=None,
            )
        ]

    def insert_transaction(self, partial: PartialTransaction):
        if self.force_insert_transaction_none:
            return None
        if partial.fingerprint in self.transaction_fingerprints:
            return None
        if partial.external_id and partial.external_id in self.transaction_external_ids:
            return None
        txn_id = len(self.transactions)
        self.transactions.append(partial)
        self.transaction_fingerprints[partial.fingerprint] = txn_id
        if partial.external_id:
            self.transaction_external_ids[partial.external_id] = txn_id
        return txn_id

    def select_transaction_id_by_fingerprint_or_external_id(
        self, fingerprint: str, external_id: str | None
    ):
        if external_id and external_id in self.transaction_external_ids:
            return self.transaction_external_ids[external_id]
        return self.transaction_fingerprints.get(fingerprint)

    def insert_budget_transaction(self, budget_id: int, transaction_id: int):
        self.inserted_budget_transactions.append((budget_id, transaction_id))

    def filter_transactions(self, **kwargs):
        start = kwargs.get("start")
        end = kwargs.get("end")
        if start and end:
            return [
                t
                for t in self.transactions
                if getattr(t, "occurred_at", None) is None
                or (start <= t.occurred_at < end)
            ]
        return list(self.transactions)

    def retrieve_transactions(self):
        return list(self.transactions)

    def update_transaction_note(self, id: int, note: str):
        self.transaction_note_updates.append((id, note))

    def select_budget_id_for_transaction(self, transaction_id: int):
        return self.selected_budget_id

    def delete_budget_transaction(self, budget_id: int, transaction_id: int):
        self.deleted_budget_transactions.append((budget_id, transaction_id))

    def retrieve_plaid_accounts(self):
        return self.plaid_accounts

    def select_plaid_account(self, account_id: int):
        return self.plaid_accounts[0]

    def select_account_by_id(self, account_id: int):
        return self.accounts_by_id[account_id]

    def account_exists_by_fingerprint(self, fingerprint: str):
        for index, account in enumerate(self.inserted_accounts, start=1):
            if account.fingerprint == fingerprint:
                return index
        return None

    def insert_account(self, partial: PartialAccount):
        self.inserted_accounts.append(partial)
        account_id = len(self.inserted_accounts)
        return account_id

    def insert_tag(self, name: str):
        return Tag(id=1, name=name)

    def retrieve_tags(self):
        return [Tag(id=1, name="Rent"), Tag(id=2, name="Food")]

    def retrieve_budget_tags(self, budget_id: int):
        return [Tag(id=3, name="Utilities")]

    def insert_budget_tag(self, budget_id: int, tag_id: int):
        self.tag_assignments.append((budget_id, tag_id))

    def delete_budget_tag(self, budget_id: int, tag_id: int):
        self.tag_assignments.append((budget_id, tag_id, "deleted"))

    def retrieve_accounts(self):
        return list(self.accounts_by_id.values())

    def insert_plaid_account(self, access_token: str):
        self.plaid_inserted_token = access_token
        return 99


@pytest.fixture(autouse=True)
def patch_plaid(monkeypatch):
    monkeypatch.setattr("core.service.Plaid", FakePlaid)


@pytest.fixture
def service():
    store = FakeStore()
    srv = Service(store)
    return srv


def test_budget_creation_and_copy(service):
    service.store.budgets = [
        Budget(0, "Old", 1000, 0, 0, datetime.datetime(2023, 1, 1)),
        Budget(1, "Keep", 2000, 0, 0, datetime.datetime(2023, 1, 1)),
    ]
    current_budget = Budget(0, "Keep", 1500, 0, 0, datetime.datetime(2023, 2, 1))
    service.store.budgets.append(current_budget)

    service.create_budget("New", 50)
    service.create_budget_from_copy(1, 2023, 2, 2023)
    service.delete_budget(0)

    assert service.store.inserted_budgets[0][0] == "New"
    copied = [b for b in service.store.inserted_budgets if b[0] == "Old"]
    assert copied and isinstance(copied[0][2], datetime.datetime)
    assert service.store.deleted_budget == 0


def test_budget_retrieval_and_updates(service):
    service.store.budgets = [
        Budget(0, "Groceries", 1000, 200, 0, datetime.datetime(2023, 1, 1)),
    ]

    all_budgets = service.get_all_budgets(1, 2023)
    got_budget = service.get_budget(0)
    service.edit_budget_name(0, "Food")
    service.edit_budget_allocated(0, 25)

    assert len(all_budgets) == 1
    assert got_budget.name == "Groceries"
    assert any(update.name == "Food" for update in service.store.budget_updates)
    assert any(update.amount_allocated == 25 for update in service.store.budget_updates)


def test_budget_overview_and_refresh_spent(service):
    service.store.budgets = [
        Budget(1, "Rent", 5000, 1200, 0, datetime.datetime(2023, 4, 1)),
        Budget(2, "Food", 2500, 300, 0, datetime.datetime(2023, 4, 1)),
    ]

    overview = service.get_budget_overview(4, 2023)
    spent = service.refresh_budget_spent(1)

    assert overview["total_allocated"] == 7500
    assert overview["total_spent"] == 1500
    assert spent == 1200
    assert service.store.budget_updates[-1].amount_spent == 1200


def test_ensure_import_account_returns_existing(service):
    fingerprint = Service._Service__build_account_fingerprint(
        "CSV", "Checking", TransactionType.DEPOSITORY, "0000"
    )
    service.store.inserted_accounts = [
        PartialAccount(
            "csv:checking",
            TransactionSource.PLAID,
            TransactionType.DEPOSITORY,
            "Checking",
            0,
            fingerprint,
        )
    ]

    account_id = service._ensure_import_account("Checking")

    assert account_id == 1


def test_transaction_creation_and_assignment(service):
    service.store.transactions = [
        Transaction(
            id=0,
            name="Original",
            amount=100,
            direction=TransactionDirection.OUT,
            occurred_at=datetime.datetime(2023, 2, 1),
            account_id=1,
            external_id=None,
            note=None,
        )
    ]
    service.store.budgets = [
        Budget(5, "Test Budget", 1000, 0, 0, datetime.datetime(2023, 3, 1)),
        Budget(2, "Secondary Budget", 500, 0, 0, datetime.datetime(2023, 3, 1)),
    ]

    txn_id = service.create_transaction("Test", -10, 1, "2023-03-01T00:00:00")
    service.create_budget_transaction(5, "BudgetTx", 20, 1, "2023-03-02T00:00:00")
    service.update_transaction_note(txn_id, "note")

    # Unassignment with missing budget
    service.store.selected_budget_id = None
    assert service.unassign_transaction_to_budget(None, txn_id) is False
    service.store.selected_budget_id = 5
    assert service.unassign_transaction_to_budget(None, txn_id) is True

    # Assignment success
    service.assign_transaction_to_budget(2, txn_id, 3, 2023)

    # Assignment with mismatch
    mismatched = Transaction(
        id=99,
        name="Mismatch",
        amount=100,
        direction=TransactionDirection.OUT,
        occurred_at="2023-02-01",
        account_id=1,
        external_id=None,
        note=None,
    )
    mismatch_id = len(service.store.transactions)
    service.store.transactions.append(mismatched)
    with pytest.raises(ValueError):
        service.assign_transaction_to_budget(2, mismatch_id, 3, 2023)

    assert service.store.inserted_budget_transactions
    assert service.store.transaction_note_updates == [(txn_id, "note")]


def test_plaid_sync(service):
    service.sync_all_transactions()

    assert len(service.store.transactions) == 2
    names = [t.name for t in service.store.transactions]
    assert "Store B" in names


def test_apple_sync(service):
    service.sync_apple_transactions([])

    apple_transactions = [
        AppleTransaction(
            id="a-1",
            account_id="apple-acc",
            name="Apple Purchase",
            amount=1234,
            direction=TransactionDirection.OUT,
            date=datetime.datetime(2023, 1, 10),
        )
    ]

    service.sync_apple_transactions(apple_transactions)

    assert service.store.inserted_accounts
    assert service.store.transactions[-1].external_id == "a-1"


def test_tag_and_account_helpers(service):
    service.store.transactions.append(
        PartialTransaction(
            "Existing",
            10,
            TransactionDirection.OUT,
            1,
            "fp",
            occurred_at=datetime.datetime(2023, 12, 15),
        )
    )
    budget_txns = service.get_all_budget_transactions(1)
    recent = service.get_all_recent_transactions(12, 2023)
    all_txns = service.get_all_transactions()

    tag = service.create_tag("New Tag")
    all_tags = service.search_tags("fo")
    budget_tags = service.get_all_budget_tags(1)
    service.assign_tag_to_budget(1, 2)
    service.unassign_tag_from_budget(1, 2)
    service.tags = service.store.tags
    service.delete_tag(1)
    accounts = service.get_all_accounts()
    link_token = service.get_plaid_token()

    assert budget_txns
    assert recent == all_txns
    assert tag.name == "New Tag"
    assert all(
        tag.name.lower().startswith("f") or tag.name.lower().startswith("r")
        for tag in all_tags
    )
    assert budget_tags and accounts
    assert service.store.tag_assignments[-1] == (1, 2, "deleted")
    assert link_token == "link-token"


def test_create_accounts_by_plaid(service):
    # Branch with no new accounts
    service.store.inserted_accounts = [
        PartialAccount(
            "acc1",
            TransactionSource.PLAID,
            TransactionType.CREDIT,
            "Existing",
            0,
            "finger1",
        ),
        PartialAccount(
            "acc2",
            TransactionSource.PLAID,
            TransactionType.CREDIT,
            "Existing",
            0,
            "finger2",
        ),
    ]
    service.create_accounts_by_plaid("public-token")
    assert service.store.plaid_inserted_token is None

    # Branch with new accounts
    service.store.inserted_accounts.clear()
    service.create_accounts_by_plaid("public-token")
    assert service.store.plaid_inserted_token == "access-public-token"
    assert any(acc.plaid_id == 99 for acc in service.store.inserted_accounts)


def test_import_transactions_from_csv_reuses_existing_transaction_id(service):
    occurred_at = datetime.datetime(2023, 5, 10)
    fingerprint = Service._Service__build_transaction_fingerprint(
        "Lunch", 12, TransactionDirection.OUT, occurred_at
    )
    existing = Transaction(
        id=0,
        name="Lunch",
        amount=12,
        direction=TransactionDirection.OUT,
        occurred_at=occurred_at,
        account_id=1,
        external_id=None,
        note=None,
    )
    service.store.transactions.append(existing)
    service.store.transaction_fingerprints[fingerprint] = 0
    service.store.budgets = [
        Budget(1, "Food", 1000, 0, 0, datetime.datetime(2023, 5, 1))
    ]

    rows = [
        {
            "occurred_at": occurred_at,
            "amount": -12,
            "account_name": "Checking",
            "description": "Lunch",
            "budget_name": "Food",
        }
    ]

    imported = service.import_transactions_from_csv(rows)

    assert imported == 1
    assert service.store.inserted_budget_transactions == [(1, 0)]


def test_import_transactions_from_csv_skips_missing_budget_name(service):
    rows = [
        {
            "occurred_at": datetime.datetime(2023, 6, 1),
            "amount": -20,
            "account_name": "Checking",
            "description": "Taxi",
        }
    ]

    imported = service.import_transactions_from_csv(rows)

    assert imported == 1
    assert service.store.inserted_budget_transactions == []


def test_import_transactions_from_csv_skips_when_transaction_unresolved(service):
    service.store.force_insert_transaction_none = True
    rows = [
        {
            "occurred_at": datetime.datetime(2023, 6, 1),
            "amount": -15,
            "account_name": "Checking",
            "description": "Snack",
            "budget_name": "Food",
        }
    ]

    imported = service.import_transactions_from_csv(rows)

    assert imported == 1
    assert service.store.inserted_budget_transactions == []


def test_import_transactions_from_csv_skips_missing_budget(service):
    service.store.budgets = [
        Budget(2, "Rent", 1500, 0, 0, datetime.datetime(2023, 6, 1))
    ]
    rows = [
        {
            "occurred_at": datetime.datetime(2023, 6, 15),
            "amount": -40,
            "account_name": "Checking",
            "description": "Parking",
            "budget_name": "Travel",
        }
    ]

    imported = service.import_transactions_from_csv(rows)

    assert imported == 1
    assert service.store.inserted_budget_transactions == []


def test_import_transactions_from_csv_skips_budget_assignment_on_mismatch(
    service,
):
    occurred_at = datetime.datetime(2023, 7, 10)
    fingerprint = Service._Service__build_transaction_fingerprint(
        "Dinner", 30, TransactionDirection.OUT, occurred_at
    )
    service.store.transactions.append(
        Transaction(
            id=0,
            name="Dinner",
            amount=30,
            direction=TransactionDirection.OUT,
            occurred_at=datetime.datetime(2023, 8, 10),
            account_id=1,
            external_id=None,
            note=None,
        )
    )
    service.store.transaction_fingerprints[fingerprint] = 0
    service.store.budgets = [
        Budget(3, "Food", 1200, 0, 0, datetime.datetime(2023, 7, 1))
    ]
    rows = [
        {
            "occurred_at": occurred_at,
            "amount": -30,
            "account_name": "Checking",
            "description": "Dinner",
            "budget_name": "Food",
        }
    ]

    imported = service.import_transactions_from_csv(rows)

    assert imported == 1
    assert service.store.inserted_budget_transactions == []


def test_assign_transaction_to_budget_parses_string_date(service):
    service.store.transactions.append(
        Transaction(
            id=0,
            name="Subscription",
            amount=25,
            direction=TransactionDirection.OUT,
            occurred_at="2023-09-05",
            account_id=1,
            external_id=None,
            note=None,
        )
    )
    service.store.budgets = [
        Budget(1, "Services", 900, 0, 0, datetime.datetime(2023, 9, 1))
    ]

    service.assign_transaction_to_budget(1, 0, 9, 2023)

    assert service.store.inserted_budget_transactions == [(1, 0)]
