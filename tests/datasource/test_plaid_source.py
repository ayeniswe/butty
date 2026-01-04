import sys
import types

import pytest

from core.datasource import plaid_source


class DummyEnvironment:
    Production = "prod"
    Sandbox = "sandbox"


class DummyConfiguration:
    def __init__(self, host=None, api_key=None):
        self.host = host
        self.api_key = api_key


class DummyApiClient:
    def __init__(self, config):
        self.config = config


class DummyLinkTokenCreateRequestUser:
    def __init__(self, client_user_id):
        self.client_user_id = client_user_id


class DummyLinkTokenCreateRequest:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class DummyProducts:
    def __init__(self, value):
        self.value = value


class DummyCountryCode:
    def __init__(self, value):
        self.value = value


class DummyItemPublicTokenExchangeRequest:
    def __init__(self, public_token):
        self.public_token = public_token


class DummyTransactionsSyncRequest:
    def __init__(self, access_token, cursor=None):
        self.access_token = access_token
        self.cursor = cursor


class DummyAccountsGetRequest:
    def __init__(self, access_token):
        self.access_token = access_token


class DummyAccount:
    def __init__(
        self,
        account_id,
        name,
        official_name,
        subtype_value,
        type_value,
        balance,
        mask=None,
    ):
        self.account_id = account_id
        self.name = name
        self.official_name = official_name
        self.subtype = type("Subtype", (), {"value": subtype_value})()
        self.type = type("Type", (), {"value": type_value})()
        self._balance = balance
        self.mask = mask

    def __getitem__(self, key):
        if key == "balances":
            return {"current": self._balance}
        raise KeyError(key)


class DummyPlaidApi:
    def __init__(self, *_args, **_kwargs):
        self.link_requests = []
        self.exchange_requests = []
        self.sync_requests = []
        self.accounts_requests = []
        self.transactions_responses = [
            {"added": ["t1"], "has_more": True, "next_cursor": "cursor-1"},
            {"added": ["t2"], "has_more": False},
        ]

    def link_token_create(self, request):
        self.link_requests.append(request)
        return {"link_token": "dummy-link-token"}

    def item_public_token_exchange(self, request):
        self.exchange_requests.append(request)
        return {"access_token": "exchanged-access-token"}

    def transactions_sync(self, request):
        self.sync_requests.append(request)
        return self.transactions_responses.pop(0)

    def accounts_get(self, request):
        self.accounts_requests.append(request)
        return {
            "item": {"institution_id": "inst-123"},
            "accounts": [
                DummyAccount("acc-1", "Check", None, "checking", "depository", 50.5),
                DummyAccount(
                    "acc-2", "Save", "Savings", "savings", "depository", 100.0
                ),
            ],
        }


# Install dummy plaid modules so importing plaid_source does not require the real SDK.
plaid_module = types.ModuleType("plaid")
plaid_module.Environment = DummyEnvironment

plaid_api_module = types.ModuleType("plaid.api.plaid_api")
plaid_api_module.PlaidApi = DummyPlaidApi

plaid_api_package = types.ModuleType("plaid.api")
plaid_api_package.plaid_api = plaid_api_module

configuration_module = types.ModuleType("plaid.configuration")
configuration_module.Configuration = DummyConfiguration

api_client_module = types.ModuleType("plaid.api_client")
api_client_module.ApiClient = DummyApiClient

country_code_module = types.ModuleType("plaid.model.country_code")
country_code_module.CountryCode = DummyCountryCode

link_user_module = types.ModuleType("plaid.model.link_token_create_request_user")
link_user_module.LinkTokenCreateRequestUser = DummyLinkTokenCreateRequestUser

link_request_module = types.ModuleType("plaid.model.link_token_create_request")
link_request_module.LinkTokenCreateRequest = DummyLinkTokenCreateRequest

products_module = types.ModuleType("plaid.model.products")
products_module.Products = DummyProducts

transaction_module = types.ModuleType("plaid.model.transaction")
transaction_module.Transaction = str

transactions_sync_module = types.ModuleType("plaid.model.transactions_sync_request")
transactions_sync_module.TransactionsSyncRequest = DummyTransactionsSyncRequest

accounts_get_module = types.ModuleType("plaid.model.accounts_get_request")
accounts_get_module.AccountsGetRequest = DummyAccountsGetRequest

item_public_token_module = types.ModuleType(
    "plaid.model.item_public_token_exchange_request"
)
item_public_token_module.ItemPublicTokenExchangeRequest = (
    DummyItemPublicTokenExchangeRequest
)

sys.modules.update(
    {
        "plaid": plaid_module,
        "plaid.api": plaid_api_package,
        "plaid.api.plaid_api": plaid_api_module,
        "plaid.configuration": configuration_module,
        "plaid.api_client": api_client_module,
        "plaid.model.country_code": country_code_module,
        "plaid.model.link_token_create_request_user": link_user_module,
        "plaid.model.link_token_create_request": link_request_module,
        "plaid.model.products": products_module,
        "plaid.model.transaction": transaction_module,
        "plaid.model.transactions_sync_request": transactions_sync_module,
        "plaid.model.accounts_get_request": accounts_get_module,
        "plaid.model.item_public_token_exchange_request": item_public_token_module,
    }
)


@pytest.fixture(autouse=True)
def patch_plaid_dependencies(monkeypatch):
    monkeypatch.setenv("ENV", "sandbox")
    monkeypatch.setenv("PLAID_CLIENT", "client")
    monkeypatch.setenv("PLAID_SANDBOX_SECRET", "sandbox-secret")

    monkeypatch.setattr(plaid_source, "Environment", DummyEnvironment)
    monkeypatch.setattr(plaid_source, "Configuration", DummyConfiguration)
    monkeypatch.setattr(plaid_source, "ApiClient", DummyApiClient)
    monkeypatch.setattr(plaid_source, "PlaidApi", DummyPlaidApi)
    monkeypatch.setattr(
        plaid_source, "LinkTokenCreateRequestUser", DummyLinkTokenCreateRequestUser
    )
    monkeypatch.setattr(
        plaid_source, "LinkTokenCreateRequest", DummyLinkTokenCreateRequest
    )
    monkeypatch.setattr(plaid_source, "Products", DummyProducts)
    monkeypatch.setattr(plaid_source, "CountryCode", DummyCountryCode)
    monkeypatch.setattr(
        plaid_source,
        "ItemPublicTokenExchangeRequest",
        DummyItemPublicTokenExchangeRequest,
    )
    monkeypatch.setattr(
        plaid_source, "TransactionsSyncRequest", DummyTransactionsSyncRequest
    )
    monkeypatch.setattr(plaid_source, "AccountsGetRequest", DummyAccountsGetRequest)


def test_plaid_requires_sdk(monkeypatch):
    monkeypatch.setattr(plaid_source, "Environment", None)

    with pytest.raises(ImportError):
        plaid_source.Plaid()


def test_create_link_builds_link_token():
    plaid = plaid_source.Plaid()

    link_token = plaid.create_link()

    assert link_token == "dummy-link-token"
    request = plaid.client.link_requests[0]
    assert request.kwargs["client_name"] == "Butty"
    assert isinstance(request.kwargs["user"], DummyLinkTokenCreateRequestUser)
    assert request.kwargs["products"][0].value == "transactions"


def test_add_financial_item_exchanges_token():
    plaid = plaid_source.Plaid()

    access_token = plaid.add_financial_item("public-token")

    assert access_token == "exchanged-access-token"
    exchange_request = plaid.client.exchange_requests[0]
    assert exchange_request.public_token == "public-token"


def test_retrieve_transactions_pages_and_aggregates():
    plaid = plaid_source.Plaid()

    transactions = plaid.retrieve_transactions("access-123")

    assert transactions == ["t1", "t2"]
    first_request, second_request = plaid.client.sync_requests
    assert first_request.access_token == "access-123"
    assert second_request.cursor == "cursor-1"


def test_retrieve_accounts_builds_domain_objects(monkeypatch):
    plaid = plaid_source.Plaid()
    fingerprints = []

    def dummy_build_fingerprint(inst_id, name, subtype, mask):
        fingerprints.append((inst_id, name, subtype, mask))
        return f"fp-{inst_id}-{name}-{subtype}-{mask}"

    monkeypatch.setattr(plaid_source, "build_fingerprint", dummy_build_fingerprint)

    accounts = plaid.retrieve_accounts("access-456")

    assert [acc.account_id for acc in accounts] == ["acc-1", "acc-2"]
    assert fingerprints[0] == ("inst-123", "Check", "checking", None)
    assert fingerprints[1] == ("inst-123", "Savings", "savings", None)
    assert accounts[0].balance == 50.5
