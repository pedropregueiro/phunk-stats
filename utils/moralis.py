import time
from collections import defaultdict

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import settings

BASE_URL = "https://deep-index.moralis.io/api/v2"

moralis_headers = {
    "Content-Type": "application/json",
    "X-API-Key": settings.MORALIS_API_KEY,
}

retry_strategy = Retry(
    total=5,
    backoff_factor=2
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)


def _paginate_request(endpoint, query_params):
    objects = []
    status = None

    fetched = -2
    total = -1

    while fetched < total:
        if fetched > 0:
            query_params['offset'] = fetched

        response = requests.get(endpoint, params=query_params, headers=moralis_headers)
        if not response.ok:
            raise Exception(f"issue fetching {endpoint}: {response.status_code} {response.text}")

        print(f"took {response.elapsed.total_seconds()}s | {response.request.url}")

        json_resp = response.json()

        result = json_resp.get('result')
        status = json_resp.get('status')

        if fetched == -2:
            fetched = len(result)
            total = json_resp.get('total')
        else:
            fetched += len(result)

        if total == 0:
            break

        # fml...
        time.sleep(1)

        objects.extend(result)

    try:
        assert len(objects) == total
    except AssertionError as e:
        print(f"totals are not equal. objects extracted {len(objects)} diff than response total field {total}")
        raise e

    print(f"query status: {status}")

    return objects


def get_nft_owners(contract_address, limit=None):
    endpoint = f"{BASE_URL}/nft/{contract_address}/owners"
    query_params = {
        "chain": "eth",
        "order": "token_id.ASC",
    }

    if limit:
        query_params["limit"] = limit

    nfts = _paginate_request(endpoint, query_params=query_params)
    return nfts


def get_nft_unique_owners(contract_address, limit=None):
    unique_owners = defaultdict(list)
    nfts = get_nft_owners(contract_address, limit=limit)
    print(f"found {len(nfts)} nfts")
    for nft in nfts:
        unique_owners[nft.get('owner_of')].append(nft.get('token_id'))

    return unique_owners
