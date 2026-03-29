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
        self.retrieve_transactions_calls = []
        self.removed_access_tokens = []

    def create_link(self):
        self.link_token_called = True
        return "link-token"

    def add_financial_item(self, public_token: str):
        return f"access-{public_token}"

    def retrieve_accounts(self, access_token: str):
        from core.datasource.model import PlaidAccountBase

        if access_token == "token-1":
            return (
                [
                    PlaidAccountBase(
                        "plaid-credit-acc", "Credit", "finger1", "credit", 1200
                    )
                ],
                "inst-1",
            )

        if access_token == "token-2":
            return (
                [
                    PlaidAccountBase(
                        "plaid-checking-acc",
                        "Checking",
                        "finger2",
                        "depository",
                        800,
                    )
                ],
                "inst-2",
            )

        return (
            [
                PlaidAccountBase("acc1", "Checking", "finger1", "depository", 1200),
                PlaidAccountBase("acc2", "Credit", "finger2", "credit", 800),
            ],
            "inst-fake",
        )

    def remove_financial_item(self, access_token: str):
        self.removed_access_tokens.append(access_token)

    def retrieve_transactions(self, access_token: str, cursor: str | None = None):
        self.retrieve_transactions_calls.append((access_token, cursor))

        class Txn:
            def __init__(
                self, name, merchant, amount, date, transaction_id, account_id, category
            ):
                self.name = name
                self.merchant_name = merchant
                self.amount = amount
                self.date = date
                self.transaction_id = transaction_id
                self.account_id = account_id
                self.personal_finance_category = category

        class Category:
            def __init__(self, primary, detailed):
                self.primary = primary
                self.detailed = detailed

        now = datetime.datetime(2023, 1, 15)
        if access_token == "token-1":
            return [
                Txn(
                    "Merchant A",
                    None,
                    2500,
                    now,
                    "t-1",
                    "plaid-credit-acc",
                    Category("FOOD_AND_DRINK", "FOOD_AND_DRINK_RESTAURANT"),
                ),
                Txn(
                    "Merchant B",
                    "Store B",
                    -500,
                    now,
                    "t-2",
                    "plaid-credit-acc",
                    Category("FOOD_AND_DRINK", "FOOD_AND_DRINK_COFFEE"),
                ),
            ], [], [], "cursor-1-new"

        return [
            Txn(
                "Rent",
                "Landlord",
                1200,
                now,
                "t-3",
                "plaid-checking-acc",
                Category("RENT_AND_UTILITIES", "RENT_AND_UTILITIES_RENT"),
            ),
            Txn(
                "Payroll",
                None,
                -4500,
                now,
                "t-4",
                "plaid-checking-acc",
                Category("INCOME", "INCOME_WAGES"),
            ),
        ], [], [], "cursor-2-new"


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
        self.plaid_accounts = [
            PlaidAccount(1, "token-1", "inst-1", "cursor-1-old"),
            PlaidAccount(2, "token-2", "inst-2", "cursor-2-old"),
        ]
        self.accounts_by_id = {
            1: Account(
                id=1,
                external_id="plaid-credit-acc",
                account_type=TransactionType.CREDIT,
                source=TransactionSource.PLAID,
                name="Credit Card",
                balance=0,
                plaid_id=1,
            ),
            2: Account(
                id=2,
                external_id="plaid-checking-acc",
                account_type=TransactionType.DEPOSITORY,
                source=TransactionSource.PLAID,
                name="Checking",
                balance=0,
                plaid_id=2,
            ),
        }
        self.tag_assignments = []
        self.budget_tags = []
        self.plaid_inserted_token = None
        self.inserted_accounts: list[PartialAccount] = []
        self.tags = [{"id": "1"}, {"id": "2"}]
        self.updated_plaid_cursors = []
        self.plaid_category_updates = []
        self.transaction_plaid_category_ids = {}
        self.plaid_categories = []
        self.plaid_mappings_by_budget: dict[int, list[int]] = {}
        self.plaid_category_lookup: dict[str, int] = {}
        self.updated_account_balances = []
        self.updated_account_display_names = []
        self.ignored_budget_transactions = set()
        self.updated_transactions = []

    def insert_budget(self, name, allocated, created_at=None):
        self.inserted_budgets.append((name, allocated, created_at))
        return len(self.inserted_budgets)

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
        txn = self.transactions[id]
        plaid_category_id = self.transaction_plaid_category_ids.get(id)
        if plaid_category_id is None:
            return txn
        return type(
            "TxnWithCategory",
            (),
            {
                "id": getattr(txn, "id", id),
                "name": txn.name,
                "amount": txn.amount,
                "direction": txn.direction,
                "occurred_at": txn.occurred_at,
                "account_id": txn.account_id,
                "external_id": getattr(txn, "external_id", None),
                "note": getattr(txn, "note", None),
                "plaid_category_id": plaid_category_id,
            },
        )()

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

    def select_transaction_id_by_external_id(self, external_id: str):
        return self.transaction_external_ids.get(external_id)

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

    def update_transaction_plaid_category(self, id: int, plaid_category_id: int):
        self.plaid_category_updates.append((id, plaid_category_id))
        self.transaction_plaid_category_ids[id] = plaid_category_id

    def update_transaction(self, id: int, partial: PartialTransaction):
        existing = self.transactions[id]
        updated = Transaction(
            id=id,
            name=partial.name,
            amount=partial.amount,
            direction=partial.direction,
            occurred_at=partial.occurred_at,
            account_id=partial.account_id,
            external_id=partial.external_id,
            note=getattr(existing, "note", None),
            plaid_category_id=self.transaction_plaid_category_ids.get(id),
        )
        self.transactions[id] = updated
        self.transaction_fingerprints[partial.fingerprint] = id
        if partial.external_id:
            self.transaction_external_ids[partial.external_id] = id
        self.updated_transactions.append(id)

    def select_budget_id_for_transaction(self, transaction_id: int):
        return self.selected_budget_id

    def delete_budget_transaction(self, budget_id: int, transaction_id: int):
        self.deleted_budget_transactions.append((budget_id, transaction_id))

    def delete_transaction(self, id: int):
        transaction = self.transactions[id]
        external_id = getattr(transaction, "external_id", None)
        if external_id:
            self.transaction_external_ids.pop(external_id, None)
        self.transactions[id] = Transaction(
            id=id,
            name="__deleted__",
            amount=0,
            direction=TransactionDirection.OUT,
            occurred_at="1970-01-01",
            account_id=1,
            external_id=None,
            note=None,
        )

    def retrieve_plaid_accounts(self):
        return self.plaid_accounts

    def select_plaid_account(self, account_id: int):
        for plaid_account in self.plaid_accounts:
            if plaid_account.id == account_id:
                return plaid_account
        raise IndexError("Plaid account not found")

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

    def update_account_balance(self, id: int, balance: float):
        self.updated_account_balances.append((id, balance))

    def update_account_display_name(self, id: int, display_name: str):
        self.updated_account_display_names.append((id, display_name))

    def insert_ignored_budget_transaction(self, budget_id: int, transaction_id: int):
        self.ignored_budget_transactions.add((budget_id, transaction_id))

    def ignored_budget_transaction_exists(self, budget_id: int, transaction_id: int):
        return (budget_id, transaction_id) in self.ignored_budget_transactions

    def update_plaid_account_cursor(self, id: int, cursor: str | None):
        self.updated_plaid_cursors.append((id, cursor))

    def upsert_plaid_category(self, primary: str, detailed: str):
        if detailed in self.plaid_category_lookup:
            return self.plaid_category_lookup[detailed]
        category_id = len(self.plaid_categories) + 1
        category = type(
            "Cat", (), {"id": category_id, "primary": primary, "detailed": detailed}
        )
        self.plaid_categories.append(category)
        self.plaid_category_lookup[detailed] = category_id
        return category_id

    def retrieve_plaid_categories(self):
        return self.plaid_categories

    def replace_budget_plaid_category_mappings(
        self, budget_id: int, plaid_category_ids: list[int]
    ):
        self.plaid_mappings_by_budget[budget_id] = list(plaid_category_ids)

    def copy_budget_plaid_category_mappings(
        self, source_budget_id: int, target_budget_id: int
    ):
        self.plaid_mappings_by_budget[target_budget_id] = list(
            self.plaid_mappings_by_budget.get(source_budget_id, [])
        )

    def retrieve_budget_plaid_category_mappings(self, budget_id: int):
        mapped_ids = set(self.plaid_mappings_by_budget.get(budget_id, []))
        result = []
        for category in self.plaid_categories:
            if category.id not in mapped_ids:
                continue
            mapping = type(
                "Mapping",
                (),
                {
                    "id": category.id,
                    "budget_id": budget_id,
                    "budget_name": "",
                    "plaid_category_id": category.id,
                    "plaid_primary": category.primary,
                    "plaid_detailed": category.detailed,
                },
            )
            result.append(mapping)
        return result

    def select_budget_id_by_plaid_category(self, detailed: str):
        budget_ids = self.select_budget_ids_by_plaid_category(detailed)
        return budget_ids[0] if budget_ids else None

    def select_budget_ids_by_plaid_category(self, detailed: str):
        category_id = self.plaid_category_lookup.get(detailed)
        if not category_id:
            return []
        return sorted(
            [
                budget_id
                for budget_id, mapped_ids in self.plaid_mappings_by_budget.items()
                if category_id in mapped_ids
            ],
            reverse=True,
        )

    def select_budget_id_by_plaid_category_id(self, plaid_category_id: int):
        budget_ids = self.select_budget_ids_by_plaid_category_id(plaid_category_id)
        return budget_ids[0] if budget_ids else None

    def select_budget_ids_by_plaid_category_id(self, plaid_category_id: int):
        return sorted(
            [
                budget_id
                for budget_id, mapped_ids in self.plaid_mappings_by_budget.items()
                if plaid_category_id in mapped_ids
            ],
            reverse=True,
        )

    def insert_plaid_account(self, access_token: str, institution_id: str | None = None):
        self.plaid_inserted_token = access_token
        institution_key = institution_id if institution_id else access_token
        self.plaid_accounts.append(PlaidAccount(99, access_token, institution_key, None))
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
    service.store.plaid_mappings_by_budget[0] = [2, 3]
    current_budget = Budget(0, "Keep", 1500, 0, 0, datetime.datetime(2023, 2, 1))
    service.store.budgets.append(current_budget)

    service.create_budget("New", 50)
    service.create_budget_from_copy(1, 2023, 2, 2023)
    service.delete_budget(0)

    assert service.store.inserted_budgets[0][0] == "New"
    copied = [b for b in service.store.inserted_budgets if b[0] == "Old"]
    assert copied and isinstance(copied[0][2], datetime.datetime)
    # new budget id falls back to count of inserted_budgets in the FakeStore
    new_id = len(service.store.inserted_budgets)
    assert service.store.plaid_mappings_by_budget.get(new_id) == [2, 3]
    assert service.store.plaid_mappings_by_budget.get(0) == [2, 3]  # source unchanged
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

    assert len(service.store.transactions) == 4
    names = [t.name for t in service.store.transactions]
    assert "Store B" in names
    transactions_by_external_id = {
        transaction.external_id: transaction
        for transaction in service.store.transactions
    }

    assert transactions_by_external_id["t-1"].direction == TransactionDirection.OUT
    assert transactions_by_external_id["t-3"].account_id == 2
    assert transactions_by_external_id["t-3"].direction == TransactionDirection.OUT
    assert transactions_by_external_id["t-4"].direction == TransactionDirection.IN
    assert service.plaid_client.retrieve_transactions_calls == [
        ("token-1", "cursor-1-old"),
        ("token-2", "cursor-2-old"),
    ]
    assert service.store.updated_plaid_cursors == [
        (1, "cursor-1-new"),
        (2, "cursor-2-new"),
    ]
    assert service.store.updated_account_balances == [
        (1, 1200),
        (2, 800),
    ]
    # Category persisted on matched transactions and tied to each inserted txn
    assert service.store.plaid_category_updates
    persisted_ids = {txn_id for txn_id, _ in service.store.plaid_category_updates}
    assert len(persisted_ids) == len(service.store.transactions)
    assert len(service.store.plaid_categories) >= 4
    detailed_values = {c.detailed for c in service.store.plaid_categories}
    assert {
        "FOOD_AND_DRINK_RESTAURANT",
        "FOOD_AND_DRINK_COFFEE",
        "RENT_AND_UTILITIES_RENT",
        "INCOME_WAGES",
    }.issubset(detailed_values)


def test_plaid_sync_respects_month_scope(service):
    # Use the fake plaid data (January 2023) but request February 2023 scope
    service.sync_all_transactions(month=2, year=2023)

    # Transactions still ingested, but no budget mappings should be created out of scope
    assert len(service.store.transactions) == 4
    assert service.store.inserted_budget_transactions == []


def test_plaid_sync_applies_removed_and_modified(service):
    # Seed an existing pending transaction that should be removed on sync.
    seeded = PartialTransaction(
        name="Pending Card Auth",
        amount=40,
        direction=TransactionDirection.OUT,
        account_id=1,
        fingerprint="fp-pending",
        external_id="pending-1",
        occurred_at=datetime.datetime(2023, 1, 10),
    )
    service.store.insert_transaction(seeded)

    class Txn:
        def __init__(self, amount: float):
            self.account_id = "plaid-credit-acc"
            self.amount = amount
            self.date = datetime.datetime(2023, 1, 10)
            self.transaction_id = "posted-1"
            self.merchant_name = "Coffee Shop"
            self.name = "Coffee Shop"
            self.personal_finance_category = type(
                "Cat",
                (),
                {
                    "primary": "FOOD_AND_DRINK",
                    "detailed": "FOOD_AND_DRINK_COFFEE",
                },
            )

    # Added + modified for the same posted transaction should not create duplicates.
    service.plaid_client.retrieve_transactions = lambda access_token, cursor=None: (
        [Txn(30.00)],
        [Txn(32.50)],
        ["pending-1"],
        "cursor-new",
    )

    service.sync_all_transactions(month=1, year=2023)

    assert service.store.select_transaction_id_by_external_id("pending-1") is None
    posted_ids = [
        idx
        for idx, txn in enumerate(service.store.transactions)
        if getattr(txn, "external_id", None) == "posted-1"
    ]
    assert len(posted_ids) == 1
    assert posted_ids[0] in service.store.updated_transactions


def test_sync_links_only_outgoing(service):
    # Make one incoming transaction category mapped; should not be linked
    class Txn:
        def __init__(self, direction):
            self.account_id = "plaid-checking-acc"
            self.amount = -100  # negative => IN per fake data mapping
            self.date = datetime.datetime(2023, 1, 5)
            self.transaction_id = "in-1"
            self.merchant_name = None
            self.name = "Refund"
            self.personal_finance_category = type(
                "Cat", (), {"primary": "INCOME", "detailed": "INCOME_WAGES"}
            )
            self.direction = direction

    service.plaid_client.retrieve_transactions_calls.clear()
    # Override retrieve_transactions to return a crafted IN transaction
    service.plaid_client.retrieve_transactions = lambda access_token, cursor=None: (
        [Txn(TransactionDirection.IN)],
        [],
        [],
        "c-new",
    )

    service.store.plaid_categories = []
    service.store.plaid_mappings_by_budget = {1: [1]}
    service.store.plaid_category_lookup = {"INCOME_WAGES": 1}
    service.store.inserted_budget_transactions = []

    service.sync_all_transactions(month=1, year=2023)

    assert service.store.inserted_budget_transactions == []


def test_relink_existing_transactions(service):
    # Set up an existing transaction that already has a stored plaid_category_id
    legacy_txn = Transaction(
        id=10,
        name="Legacy",
        amount=1000,
        direction=TransactionDirection.OUT,
        occurred_at="2024-01-01",
        account_id=1,
        external_id="legacy-1",
        note="",
        plaid_category_id=2,
    )
    service.store.transactions.append(legacy_txn)

    # Map category id 2 to budget 7 and ensure budget exists
    service.store.budgets.append(
        Budget(7, "Legacy Budget", 500, 0, 0, datetime.datetime(2024, 1, 1))
    )
    service.store.plaid_mappings_by_budget[7] = [2]
    service.store.selected_budget_id = None

    service.sync_all_transactions(month=1, year=2024)

    assert (7, 10) in service.store.inserted_budget_transactions


def test_relink_prefers_current_month_budget_when_category_is_reused(service):
    txn = Transaction(
        id=11,
        name="Restaurant",
        amount=2000,
        direction=TransactionDirection.OUT,
        occurred_at="2024-03-05",
        account_id=1,
        external_id="legacy-2",
        note="",
        plaid_category_id=4,
    )
    service.store.transactions.append(txn)

    service.store.budgets.extend(
        [
            Budget(1, "Food Feb", 500, 0, 0, datetime.datetime(2024, 2, 1)),
            Budget(2, "Food Mar", 500, 0, 0, datetime.datetime(2024, 3, 1)),
        ]
    )
    service.store.plaid_mappings_by_budget = {1: [4], 2: [4]}

    service.sync_all_transactions(month=3, year=2024)

    assert (2, 11) in service.store.inserted_budget_transactions
    assert (1, 11) not in service.store.inserted_budget_transactions


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
    service.edit_account_display_name(1, "Travel Card")
    link_token = service.get_plaid_token()

    assert budget_txns
    assert recent == all_txns
    assert tag.name == "New Tag"
    assert all(
        tag.name.lower().startswith("f") or tag.name.lower().startswith("r")
        for tag in all_tags
    )
    assert budget_tags and accounts
    assert service.store.updated_account_display_names[-1] == (1, "Travel Card")
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
    service.store.plaid_accounts = [
        PlaidAccount(1, "token-existing", "inst-fake", "cursor-old")
    ]
    duplicate_result = service.create_accounts_by_plaid("public-token")
    assert service.store.plaid_inserted_token is None
    assert duplicate_result == {
        "linked_new_accounts": 0,
        "duplicate_item_detected": True,
    }
    assert service.plaid_client.removed_access_tokens == ["access-public-token"]

    # Branch with new accounts
    service.store.inserted_accounts.clear()
    service.store.plaid_accounts = []
    linked_result = service.create_accounts_by_plaid("public-token")
    assert service.store.plaid_inserted_token == "access-public-token"
    assert any(acc.plaid_id == 99 for acc in service.store.inserted_accounts)
    assert linked_result == {
        "linked_new_accounts": 2,
        "duplicate_item_detected": False,
    }


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


def test_set_budget_plaid_category_mappings_and_auto_assignment(service):
    service.store.budgets = [
        Budget(7, "Daily Ritual", 1000, 0, 0, datetime.datetime(2023, 1, 1))
    ]
    service.store.inserted_budget_transactions.clear()

    service.set_budget_plaid_category_mappings(
        7, ["FOOD_AND_DRINK:FOOD_AND_DRINK_RESTAURANT"]
    )
    # Limit scope to January 2023 to pick up the fake transactions
    service.sync_all_transactions(month=1, year=2023)

    assert service.store.plaid_mappings_by_budget[7]
    # Transaction 0 is the restaurant (OUT) transaction in FakePlaid
    assert (7, 0) in service.store.inserted_budget_transactions


def test_auto_assignment_skips_other_month_budget(service):
    # Budget created in March; sync January transactions should not link
    service.store.budgets = [
        Budget(8, "March Budget", 800, 0, 0, datetime.datetime(2023, 3, 1))
    ]
    service.set_budget_plaid_category_mappings(
        8, ["FOOD_AND_DRINK:FOOD_AND_DRINK_RESTAURANT"]
    )

    service.sync_all_transactions(month=1, year=2023)

    assert (8, 0) not in service.store.inserted_budget_transactions


def test_set_budget_plaid_category_mappings_noop_on_new_budget(service):
    # Existing budget mappings untouched when setting empty mappings on a new budget
    service.store.plaid_mappings_by_budget = {1: [1, 2]}
    service.set_budget_plaid_category_mappings(99, [])

    assert service.store.plaid_mappings_by_budget[1] == [1, 2]
    assert 99 not in service.store.plaid_mappings_by_budget


def test_set_budget_plaid_category_mappings_preserves_existing_on_empty(service):
    service.store.plaid_mappings_by_budget = {1: [4, 5]}

    # Passing empty mapped_categories should keep existing mappings
    service.set_budget_plaid_category_mappings(1, [])

    assert service.store.plaid_mappings_by_budget[1] == [4, 5]


def test_sync_uses_tag_match_for_budget_assignment(service):
    service.store.budgets = [Budget(9, "Coffee", 1000, 0, 0, datetime.datetime(2023, 1, 1))]

    def retrieve_budget_tags(budget_id: int):
        if budget_id == 9:
            return [Tag(id=5, name="merchant a")]
        return []

    service.store.retrieve_budget_tags = retrieve_budget_tags
    service.store.plaid_mappings_by_budget = {}
    service.store.plaid_category_lookup = {}

    service.sync_all_transactions(month=1, year=2023)

    assert (9, 0) in service.store.inserted_budget_transactions


def test_ignore_transaction_for_budget_blocks_future_budget_mapping(service):
    service.sync_all_transactions(month=1, year=2023)

    service.store.budgets = [
        Budget(1, "Food", 1000, 0, 0, datetime.datetime(2023, 1, 1))
    ]
    service.store.selected_budget_id = 1
    ignored = service.ignore_transaction_for_budget(0)
    assert ignored is True

    service.store.inserted_budget_transactions.clear()
    service.sync_all_transactions(month=1, year=2023)

    assert service.store.ignored_budget_transaction_exists(1, 0)
    assert (1, 0) not in service.store.inserted_budget_transactions


def test_ignore_transaction_for_budget_returns_false_when_unassigned(service):
    service.store.selected_budget_id = None
    assert service.ignore_transaction_for_budget(123) is False
