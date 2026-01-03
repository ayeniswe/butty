import os

from plaid import Environment
from plaid.api.plaid_api import PlaidApi
from plaid.api_client import ApiClient
from plaid.configuration import Configuration
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.transaction import Transaction
from plaid.model.transactions_sync_request import TransactionsSyncRequest

from core.datasource.model import PlaidAccountBase
from core.utils import build_fingerprint


class Plaid:
    def __init__(self):
        isProd = os.environ["ENV"] == "prod"
        config = Configuration(
            host=Environment.Production if isProd else Environment.Sandbox,
            api_key={
                "clientId": os.environ["PLAID_CLIENT"],
                "secret": os.environ[
                    "PLAID_PRODUCTION_SECRET" if isProd else "PLAID_SANDBOX_SECRET"
                ],
            },
        )
        self.client = PlaidApi(ApiClient(config))

    @staticmethod
    def __build_fingerprint(inst_id: str, name: str, subtype: str, mask: str):
        return build_fingerprint(inst_id, name, subtype, mask)

    def create_link(self) -> str:
        request = LinkTokenCreateRequest(
            client_name="Butty",
            language="en",
            country_codes=[CountryCode("US")],
            user=LinkTokenCreateRequestUser(
                client_user_id="Butty"  # Since personal will just be the same all around
            ),
            products=[Products("transactions")],
        )
        return self.client.link_token_create(request)["link_token"]

    def add_financial_item(self, public_token: str):
        exchange_request = ItemPublicTokenExchangeRequest(public_token=public_token)
        exchange_response = self.client.item_public_token_exchange(exchange_request)
        return exchange_response["access_token"]

    def retrieve_transactions(self, access_token: str) -> list[Transaction]:
        request = TransactionsSyncRequest(access_token=access_token)
        response = self.client.transactions_sync(request)
        transactions = response["added"]

        while response["has_more"]:
            request = TransactionsSyncRequest(
                access_token=access_token, cursor=response["next_cursor"]
            )
            response = self.client.transactions_sync(request)
            transactions += response["added"]

        return transactions

    def retrieve_accounts(self, access_token: str) -> list[PlaidAccountBase]:
        request = AccountsGetRequest(access_token=access_token)
        response = self.client.accounts_get(request)

        accounts = []
        for acc in response["accounts"]:
            accounts.append(
                PlaidAccountBase(
                    acc.account_id,
                    acc.name,
                    Plaid.__build_fingerprint(
                        response["item"]["institution_id"],
                        acc.official_name or acc.name,
                        acc.subtype.value,
                        acc.mask,
                    ),
                    acc.type.value,
                    acc["balances"]["current"],
                )
            )

        return accounts
