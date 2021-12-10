import math

import requests
from web3 import Web3

CARGO_BASE_ENDPOINT_URL = "https://api3.cargo.build/v3"


def get_tokens_for_sale(project_id, filters=None, limit=200, chain="eth", result_size=None):
    endpoint = f"{CARGO_BASE_ENDPOINT_URL}/get-resale-items"
    page = 1

    query_params = {
        "sort": "low-to-high",
        "chain": chain,
        "projectId": project_id,
        "filter": {},
        "page": page,
        "limit": limit
    }

    total_pages = math.inf
    results = []
    tokens = []
    floor = None

    while page < total_pages:
        response = requests.get(endpoint, params=query_params)
        print(f"took {response.elapsed.total_seconds()}s | {response.request.url}")
        json_resp = response.json()
        page += 1
        query_params['page'] = page
        total_pages = int(json_resp.get('totalPages'))

        results.extend(json_resp.get('results'))

    # TODO: this logic could definitely be improved and added into the loop. might not be worth it
    #  as we stop using cargo.
    counter = 0
    for token in results:
        token_id = token.get('tokenId')
        attrs = token.get('metadata').get('attributes')
        if not attrs:
            print(f"did not find attributes for #{token_id}. ignoring...")
            continue

        matched = []
        if not filters:
            matched = [True]
        else:
            for tfilter in filters:
                if tfilter in attrs:
                    matched.append(True)
                else:
                    matched.append(False)

        if not all(matched):
            continue

        price = Web3.fromWei(int(float(token.get('price'))), 'ether')
        if not floor:
            floor = price

        std_dev_floor = price - floor

        tokens.append({
            "token_id": token_id,
            "price_eth": price,
            "floor": floor,
            "floor_stddev": std_dev_floor,
            "raw": token,
        })
        counter += 1

        if result_size and counter >= result_size:
            break

    return tokens
