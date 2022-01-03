import math
from statistics import mean, stdev, NormalDist

import arrow

import settings
from utils.database import get_latest_rarity_tweet, save_latest_rarity_tweet
from utils.nll_marketplace import get_tokens_for_sale
from utils.phunks import get_phunk_image_url, get_phunk_rarity
from utils.twitter import tweet


def get_percentiles(data, percentile):
    n = len(data)
    p = n * percentile / 100
    if p.is_integer():
        return sorted(data)[int(p)]
    else:
        return sorted(data)[int(math.ceil(p)) - 1]


def get_floor_deviation_phunk(traits_filter=None):
    print(f"filters: {traits_filter}")
    no_fetch = 5
    top_tokens = get_tokens_for_sale(filters=traits_filter, result_size=no_fetch)

    if not top_tokens:
        return None, None, None

    for token in top_tokens:
        token['rarity'] = get_phunk_rarity(token.get('token_id'))

    prices = [token.get('price_eth') for token in top_tokens]
    if len(prices) < 2:
        print("not enough tokens for sale")
        return None, None, None

    mean_prices = mean(prices)
    stddev_prices = stdev(prices)

    dist = NormalDist(mu=mean_prices, sigma=stddev_prices)
    zscore_dist = [dist.zscore(float(price)) for price in prices]

    below_tokens = []
    for index, score in enumerate(zscore_dist):
        # less than DEVIATING_ZSCORE standard deviation away from floor average should be snipable
        if score < settings.SNIPER_DEVIATING_ZSCORE:
            below_tokens.insert(index, top_tokens[index])

    if not below_tokens:
        print("no snipable phunks found!")

    return below_tokens, mean_prices, stddev_prices


def get_top_rarity_phunks(traits_filter=None, percentile=settings.SNIPING_FLOOR_PERCENTILE):
    print(f"filters: {traits_filter} | percentile: {percentile}")
    top_tokens = get_tokens_for_sale(filters=traits_filter, result_size=100)

    for token in top_tokens:
        token['rarity'] = get_phunk_rarity(token.get('token_id'))

    all_prices = [token.get('price_eth') for token in top_tokens]
    percentile = get_percentiles(all_prices, percentile)

    min_tokens = []
    min_rarity_tokens = []
    for top_token in top_tokens:
        token_rarity = top_token.get('rarity')
        token_price = top_token.get('price_eth')

        if token_price > percentile:
            continue

        if len(min_rarity_tokens) < 3:
            min_tokens.append(top_token)
            min_rarity_tokens.append(token_rarity)
            continue

        current_min_rarity = max(min_rarity_tokens)

        if token_rarity < current_min_rarity:
            to_remove = max(min_rarity_tokens)
            to_remove_index = min_rarity_tokens.index(to_remove)
            del min_rarity_tokens[to_remove_index]
            del min_tokens[to_remove_index]

            min_tokens.insert(to_remove_index, top_token)
            min_rarity_tokens.insert(to_remove_index, token_rarity)

    sorted_tokens = [token for token in sorted(min_tokens, key=lambda item: item.get('rarity'))]

    for token in sorted_tokens:
        print(f"#{token.get('token_id')} has rarity {token.get('rarity')}/10k at Ξ{token.get('price_eth'):.2f}")

    return sorted_tokens


def fetch_snipable_phunks(filters=None, percentile=settings.SNIPING_FLOOR_PERCENTILE, kind='rarity'):
    if len(filters) > 1:
        raise NotImplementedError("not expecting more than 1 filter. DB will be upset")

    filter_ = filters[0]
    last_tweeted = get_latest_rarity_tweet(trait_name=filter_.get('key'), trait_value=filter_.get('value'))
    last_tweeted_token_id = None
    last_tweeted_diff_seconds = 1
    if last_tweeted:
        last_tweeted_token_id = last_tweeted.get('token_id')
        last_tweeted_date = arrow.get(last_tweeted.get('created_at'))
        last_tweeted_diff_seconds = (arrow.utcnow() - last_tweeted_date).seconds

    second_liner = None
    if not kind or kind == 'rarity':
        top_phunks = get_top_rarity_phunks(traits_filter=filters, percentile=percentile)
        title = "Floor rarity scoop"
    elif kind == 'deviation':
        top_phunks, mean_price, _ = get_floor_deviation_phunk(traits_filter=filters)
        title = "Snipe! Outlier spotted"
        if mean_price:
            second_liner = f"NLL first row average Ξ{mean_price:.2f}"
    else:
        return

    if not top_phunks:
        return

    phunk = top_phunks[0]
    phunk_id = phunk.get('token_id')
    if phunk_id == last_tweeted_token_id and last_tweeted_diff_seconds < (12 * 60 * 60):  # 12 hours in seconds
        return

    tweet_text = f"""🧹 {title} // {filter_.get('key')}: {filter_.get('value')} 🧹

PHUNK #{phunk.get('token_id').zfill(4)} listed for Ξ{phunk.get('price_eth'):.2f} (rarity {phunk.get('rarity')} / 10k)
{second_liner if second_liner else ""}

https://notlarvalabs.com/market/view/phunk/{phunk.get('token_id')}
"""

    image_url = get_phunk_image_url(phunk.get("token_id"))

    print("\n\nTweeting scoop!")
    print(tweet_text)

    save_latest_rarity_tweet({"token_id": phunk.get('token_id'),
                              "trait_name": filter_.get('key'),
                              "trait_value": filter_.get('value')})
    tweet(tweet_text, image_urls=[image_url])


if __name__ == '__main__':
    filters = [{'key': 'Hair', 'value': 'Orange Side'}]
    fetch_snipable_phunks(filters=filters, kind="deviation")
