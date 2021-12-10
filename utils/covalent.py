from collections import defaultdict

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import settings

retry_strategy = Retry(
    total=3,
    backoff_factor=2
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)

COVALENT_BASE_URL = "https://api.covalenthq.com/v1/1"

covalent_default_headers = {
    "Content-Type": "application/json",
}

covalent_default_params = {
    "quote-currency": "USD",
    "format": "JSON",
    "key": settings.COVALENT_API_KEY
}


def _paginate_request(endpoint, params):
    page_size = 500
    page = 0

    params = {
        **params,
        "page-size": page_size,
        "page-number": page
    }

    has_more = True

    results = []
    while has_more:
        response = http.get(endpoint, params=params)
        if not response.ok:
            raise Exception(f"problems with request. {response.status_code} {response.text}")

        print(f"took {response.elapsed.total_seconds()}s | {response.request.url}")

        json_response = response.json()
        data = json_response.get('data')
        items = data.get('items')
        pagination = data.get('pagination')
        has_more = pagination.get('has_more') if pagination else False

        results.extend(items)

        page += 1
        params["page-number"] = page

    return results


def get_nft_owners(contract_address):
    endpoint = f"{COVALENT_BASE_URL}/tokens/{contract_address}/token_holders/"
    query_params = {
        **covalent_default_params,
        "block-height": "latest"
    }

    results = _paginate_request(endpoint, params=query_params)
    return results


def get_nft_unique_owners(contract_address):
    unique_owners = defaultdict(int)
    nfts = get_nft_owners(contract_address)

    # TODO: sort this out!
    for nft in nfts:
        unique_owners[nft.get('address')] = nft.get('balance')

    return unique_owners
