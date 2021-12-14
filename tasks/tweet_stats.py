import argparse
import copy
import json
import operator
import os
import sys
import time
from collections import defaultdict
from datetime import timedelta

import arrow
import pymongo
import schedule

import settings
from lib.web3_helpers.common.node import get_ens_domain_for_address, get_curated_nfts_holdings
from utils.database import get_latest_stats, get_holder, update_holder, save_holder, save_stats
from utils.moralis import get_nft_unique_owners
from utils.twitter import tweet

# TODO: This needs a lot of love... It was made in one go and barely touched ever since. A lot of room for errors,
# a lot of edge cases not accounted for, etc. All in all, it has been working smoothly for the last couple of months,
# but a little love never hurt anyone :phunkfam:


# TODO: move this to helper...
mongo_client = pymongo.MongoClient(settings.MONGO_CONN_STRING)
holders_coll = mongo_client['phunks']['holders']

DEEP_FETCH = os.environ.get("DEEP_FETCH", True)  # change this to False to make things quicker

# script can be executed as cli for testing or one-time runs
my_parser = argparse.ArgumentParser()
my_parser.add_argument('-r', '--run', action="store_true")
my_parser.add_argument('-s', '--silent', action="store_true")

args = my_parser.parse_args()
should_run_now = args.run
should_tweet = not args.silent

with open(os.path.join("data", "curated.json")) as f:
    curated = json.loads(f.read())


def get_progress_bar(percentage, bars=20):
    percentage = percentage * 100
    rounded_percentage = round(percentage / 10, 2) * 10
    final_value = round((rounded_percentage * bars), 2) / 100
    final_value = round(final_value)

    progress_bar = ""
    for i in range(bars):
        if i < final_value:
            progress_bar += "▓"
        else:
            progress_bar += "░"

    return progress_bar


def get_diff(old, new):
    if not old:
        diff = new
    else:
        diff = new - old

    if diff == 0:
        return None

    return f"+{diff}" if diff > 0 else f"{diff}"


def get_stats_diff(symbol, tokens, previous_stats):
    if not previous_stats:
        return ""

    previous_symbol_totals = previous_stats.get('all_holdings').get(symbol)
    diff = get_diff(previous_symbol_totals, tokens)
    if not diff:
        return ""

    return f"({diff})"


def get_holders_diff(previous_stats, current_holders, last_checked, last_checked_date):
    diff = get_diff(previous_stats.get('unique'), len(current_holders))
    if not last_checked or not diff:
        return None
    return f"({diff} since {last_checked_date.humanize()})"


def fetch_phunks_stats():
    print("Getting unique NFT owners...")

    try:
        previous_stats = get_latest_stats()
        created_at = previous_stats.get('created_at')
        created_at_arrow = arrow.get(created_at)
        time_diff = (arrow.utcnow() - created_at_arrow)  # type: timedelta
        if time_diff.seconds < (120 * 60):  # 2 hours in seconds
            print("trying to run too early, ignoring...")
            return
    except Exception as e:
        print(f"problem fetching previous stats {e}")
        previous_stats = {}

    holders = get_nft_unique_owners(settings.PHUNK_CONTRACT_ADDRESS)
    phunk_holders = copy.deepcopy(holders)
    print(f"Found {len(holders)}. Iterating through...")

    current_holder_addresses = list(holders.keys())

    sum_holdings = defaultdict(int)
    unique_holders = defaultdict(int)

    new_holders = holders_coll.find({"_id": {"$nin": current_holder_addresses}})
    if not list(new_holders) and not DEEP_FETCH:
        print("No new holders")
        sys.exit(0)

    new_holders_addresses = [h.get('_id') for h in list(new_holders)]

    total_holders = len(phunk_holders)
    counter = 1
    for holder, token_ids in holders.items():
        counter += 1
        print(f"Handling holder {holder} | {counter}/{total_holders}")
        new_holder = holder in new_holders_addresses

        db_holder = get_holder(holder)

        try:
            if not new_holder and not DEEP_FETCH and db_holder:
                curated_holdings = db_holder.get('holdings')
            else:
                curated_holdings = get_curated_nfts_holdings(holder, include_batch=False)
        except Exception as e:
            print(f"problems feching holdings for {holder}: {e}")
            continue

        ch_tuples = []
        for curated_holding in curated_holdings:
            name = curated_holding.get('name')
            balance = curated_holding.get('balance')
            symbol = curated_holding.get('symbol')
            ch_tuples.append((symbol, balance))
            sum_holdings[symbol] += balance
            unique_holders[symbol] += 1

        if len(ch_tuples) > 0:
            print(f"{holder}: {ch_tuples}")

        try:
            if db_holder:
                update_holder(holder, {'token_ids': token_ids, 'holdings': curated_holdings})
            else:
                holder_data = {
                    '_id': holder,
                    'ens': get_ens_domain_for_address(holder),
                    'token_ids': token_ids,
                    'holdings': curated_holdings
                }
                save_holder(holder_data)
        except Exception as e:
            raise e

    print("\n\n## All holdings")
    sorted_holdings = dict(sorted(dict(sum_holdings).items(), key=operator.itemgetter(1), reverse=True))
    print(sorted_holdings)

    print("\n\n## Unique holders")
    sorted_holders = dict(sorted(dict(unique_holders).items(), key=operator.itemgetter(1), reverse=True))
    print(sorted_holders)

    try:
        save_stats({'results': sorted_holders, 'unique': len(phunk_holders), 'all_holdings': sorted_holdings})
    except Exception as e:
        print(f"problem storing stats: {e}")

    last_checked = None if not previous_stats else previous_stats.get('created_at')
    last_checked_date = arrow.get(last_checked) if last_checked else None

    print("\n\nCleaning up...")
    result = holders_coll.delete_many({"_id": {"$nin": current_holder_addresses}})
    print(f"deleted {result.deleted_count} old holders")

    print("\n\nTweeting holdings...")

    for addr, meta in curated.items():
        symbol = meta.get('symbol')
        if not meta.get('show_holdings', True):
            del sorted_holdings[symbol]

    unique_holdings = [f"- {no_tokens} {symbol} {get_stats_diff(symbol, no_tokens, previous_stats)}" for
                       symbol, no_tokens in sorted_holdings.items()]
    unique_holdings_str = "\n".join(unique_holdings)

    holders_diff = get_holders_diff(previous_stats, phunk_holders, last_checked, last_checked_date)

    tweet_content = f"""Wallets holding PHUNKS also hold:

{unique_holdings_str}

{"" if not last_checked_date else f"(since {last_checked_date.humanize()})"}
"""
    print(tweet_content)
    if should_tweet:
        tweet(tweet_content)

    print("\n\nTweeting unique holders...")

    unique_owners = {}
    for addr, meta in curated.items():
        if not meta.get('show_flip', True):
            continue
        hdrs = get_nft_unique_owners(addr)
        symbol = meta.get('symbol')
        print(f"unique holders of {symbol}: {len(hdrs)}")
        unique_owners[symbol] = len(phunk_holders) / len(hdrs)

    print(unique_owners)
    sorted_percentages = dict(sorted(dict(unique_owners).items(), key=operator.itemgetter(1)))

    unique_holdings = []
    for symbol, perc in sorted_percentages.items():
        progress_bar = get_progress_bar(perc, bars=10)
        flipped = max(((1 - perc) * 100), 0)
        if flipped == 0:
            flipped_str = "PHLIPPED!"
        else:
            flipped_str = f"{flipped:.0f}%"
        holding_str = f"{progress_bar} {symbol} {flipped_str}"
        unique_holdings.append(holding_str)

    unique_holdings_str = "\n".join(unique_holdings)

    tweet_content = f"""unique PHUNK holders
{len(phunk_holders)} {"" if not holders_diff else holders_diff}

% left to flip unique holders:
{unique_holdings_str}
"""
    print(tweet_content)
    if should_tweet:
        tweet(tweet_content)


if should_run_now:
    fetch_phunks_stats()
else:
    # UTC times
    schedule.every().day.at("05:00").do(fetch_phunks_stats)
    schedule.every().day.at("17:00").do(fetch_phunks_stats)

    while True:
        try:
            schedule.run_pending()
            time.sleep(60)
        except Exception as e:
            continue
