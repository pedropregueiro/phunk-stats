import requests
from web3 import Web3

NLL_BASE_ENDPOINT_URL = "https://nll-backend-9qj3q.ondigitalocean.app"


def get_tokens_for_sale(filters=None, result_size=None):
    endpoint = f"{NLL_BASE_ENDPOINT_URL}/static/phunks-market-data"

    # use "key", "value" instead "trait_type", "value"
    for index, filter_ in enumerate(filters):
        new_filter = {"key": filter_.get("trait_type"), "value": filter_.get("value")}
        filters[index] = new_filter

    tokens = []
    floor = None

    response = requests.get(endpoint)
    print(f"took {response.elapsed.total_seconds()}s | {response.request.url}")
    json_resp = response.json()
    tokens_for_sale = json_resp.get("phunksOfferedForSale")

    # TODO: for now data returned is unsorted and unfiltered. can be improved later once API supports it
    list_tokens_for_sale = [value for key, value in tokens_for_sale.items()]
    sorted_tokens = [token for token in sorted(list_tokens_for_sale, key=lambda item: int(item.get('minValue')))]

    counter = 0
    for token in sorted_tokens:
        token_id = token.get("phunkIndex")
        attrs = token.get("data").get("properties")
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

        original_price = token.get("minValue")
        price = Web3.fromWei(int(float(original_price)), 'ether')
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
