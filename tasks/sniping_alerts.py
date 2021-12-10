import csv
import math
import os
import time
from statistics import mean, stdev, NormalDist

import arrow
import schedule as schedule

import settings
from utils.cargo import get_tokens_for_sale
from utils.database import get_latest_rarity_tweet, save_latest_rarity_tweet
from utils.twitter import tweet

rankings = {}

with open(os.path.join("data", "phunk_rankings.csv"), mode='r') as csv_file:
    csv_reader = csv.DictReader(csv_file)
    for row in csv_reader:
        rankings[int(row.get('id'))] = row.get('ranking')


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
    top_tokens = get_tokens_for_sale(project_id=settings.CARGO_PROJECT_ID, filters=traits_filter, result_size=no_fetch)

    if not top_tokens:
        return None, None, None

    for token in top_tokens:
        token['rarity'] = rankings[int(token.get('token_id'))]

    prices = [token.get('price_eth') for token in top_tokens]
    mean_prices = mean(prices)
    stddev_prices = stdev(prices)

    dist = NormalDist(mu=mean_prices, sigma=stddev_prices)
    zscore_dist = [dist.zscore(float(price)) for price in prices]

    below_tokens = []
    for index, score in enumerate(zscore_dist):
        # less than 1 standard deviation away from floor average should be snipable
        if score < -1:
            below_tokens.insert(index, top_tokens[index])

    return below_tokens, mean_prices, stddev_prices


def get_top_rarity_phunks(traits_filter=None, percentile=settings.SNIPING_FLOOR_PERCENTILE):
    print(f"filters: {traits_filter} | percentile: {percentile}")
    top_tokens = get_tokens_for_sale(project_id=settings.CARGO_PROJECT_ID, filters=traits_filter, result_size=100)

    for token in top_tokens:
        token['rarity'] = rankings[int(token.get('token_id'))]

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


def tweet_snipable_phunks(filters=None, percentile=settings.SNIPING_FLOOR_PERCENTILE, kind='rarity'):
    if len(filters) > 1:
        raise NotImplementedError("not expecting more than 1 filter. DB will be upset")

    filter_ = filters[0]
    last_tweeted = get_latest_rarity_tweet(trait_name=filter_.get('trait_type'), trait_value=filter_.get('value'))
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

    tweet_text = f"""🧹 {title} // {filter_.get('trait_type')}: {filter_.get('value')} 🧹

PHUNK #{phunk.get('token_id').zfill(4)} listed for Ξ{phunk.get('price_eth'):.2f} (rarity {phunk.get('rarity')} / 10k)
{second_liner if second_liner else ""}

https://notlarvalabs.com/market/view/phunk/{phunk.get('token_id')}
"""

    metadata = phunk.get('raw').get('metadata')
    image_url = metadata.get('image_url')
    if image_url and 'pinata.cloud' in image_url:
        # Pinata cloud has some serious rate limiting
        image_url = image_url.replace('https://gateway.pinata.cloud/', 'https://cloudflare-ipfs.com/')

    print("\n\nTweeting scoop!")
    print(tweet_text)

    save_latest_rarity_tweet({"token_id": phunk.get('token_id'),
                              "trait_name": filter_.get('trait_type'),
                              "trait_value": filter_.get('value')})
    tweet(tweet_text, image_url=image_url)


male_trait = [{'trait_type': 'Sex', 'value': 'Male'}]
female_trait = [{'trait_type': 'Sex', 'value': 'Female'}]

schedule.every(120).to(360).minutes.do(tweet_snipable_phunks, filters=male_trait)
schedule.every(120).to(360).minutes.do(tweet_snipable_phunks, filters=female_trait)

all_trait_scoops = [
    [{'trait_type': 'Mouth', 'value': 'Medical Mask'}],
    [{'trait_type': 'Neck', 'value': 'Gold Chain'}],
    [{'trait_type': 'Beard', 'value': 'Luxurious Beard'}],
    [{'trait_type': 'Beard', 'value': 'Big Beard'}],
    [{'trait_type': 'Cheeks', 'value': 'Rosy Cheeks'}],
    [{'trait_type': 'Eyes', 'value': 'Green Eye Shadow'}],
    [{'trait_type': 'Eyes', 'value': 'Purple Eye Shadow'}],
    [{'trait_type': 'Eyes', 'value': 'Blue Eye Shadow'}],
    [{'trait_type': 'Eyes', 'value': 'Vr'}],
    [{'trait_type': 'Eyes', 'value': '3D Glasses'}],
    [{'trait_type': 'Eyes', 'value': 'Welding Goggles'}],
    [{'trait_type': 'Face', 'value': 'Spots'}],
    [{'trait_type': 'Teeth', 'value': 'Buck Teeth'}],
    [{'trait_type': 'Hair', 'value': 'Orange Side'}],
    [{'trait_type': 'Hair', 'value': 'Hoodie'}],
    [{'trait_type': 'Hair', 'value': 'Beanie'}],
    [{'trait_type': 'Hair', 'value': 'Half Shaved'}],
    [{'trait_type': 'Hair', 'value': 'Wild White Hair'}],
    [{'trait_type': 'Hair', 'value': 'Top Hat'}],
    [{'trait_type': 'Hair', 'value': 'Cowboy Hat'}],
    [{'trait_type': 'Hair', 'value': 'Red Mohawk'}],
    [{'trait_type': 'Hair', 'value': 'Pink With Hat'}],
    [{'trait_type': 'Hair', 'value': 'Clown Hair Green'}],
    [{'trait_type': 'Nose', 'value': 'Clown Nose'}],
    [{'trait_type': 'Emotion', 'value': 'Smile'}],
    # TODO: need to change Cargo stuff to allow for this
    # [{'trait_type': 'Trait Count', 'value': '1'}],
    # [{'trait_type': 'Trait Count', 'value': '5'}],
]

for scoop in all_trait_scoops:
    schedule.every(120).to(480).seconds.do(tweet_snipable_phunks, filters=scoop, kind='deviation')

print("Sniping alerts scheduled...")
while True:
    schedule.run_pending()
    time.sleep(30)
