import csv
import json
import os
import re

import tweepy
from tweepy.models import Status
from web3 import Web3

import settings
from lib.web3_helpers.common.node import get_ens_domain_for_address, get_transaction, get_curated_nfts_holdings, \
    get_nft_holdings, decode_contract_transaction
from utils.coinbase import get_latest_eth_price
from utils.database import save_sale
from utils.nll_marketplace import get_tokens_for_sale
from utils.twitter import get_tweet, create_stream, reply

tx_hash_pattern = re.compile(r'tx/(.+?)$', re.IGNORECASE)

rankings = {}
with open(os.path.join("data", "phunk_rankings.csv"), mode='r') as csv_file:
    csv_reader = csv.DictReader(csv_file)
    for row in csv_reader:
        rankings[int(row.get('id'))] = row.get('ranking')

with open(os.path.join("data", "curated.json")) as f:
    curated_contracts = json.loads(f.read())


def get_short_address(address):
    short_addr = f"{address[:6]}...{address[-4:]}"
    ens_addr = get_ens_domain_for_address(address)
    return ens_addr if ens_addr else short_addr


def handle_transaction(tx_hash, tweet_id=None, phunk_id=None, etherscan_link=None):
    tx = get_transaction(tx_hash)
    print(f"transaction: {tx_hash}")

    seller = tx.get('to')
    buyer = tx.get('from')
    price = tx.get('value')
    price_eth = Web3.fromWei(int(price), 'ether')

    tx_fn, tx_input = decode_contract_transaction(tx_hash)
    function_name = tx_fn.fn_name
    print(f"function: {function_name}")
    print(f"input: {tx_input}")

    buyer_ens = get_ens_domain_for_address(buyer)
    buyer_short = f"{buyer[:6]}...{buyer[-4:]}"

    if buyer_ens:
        buyer_short = buyer_ens

    if function_name == "enterBidForPhunk":
        print("ignore bid tweets for now...")
        return

    tweet_text = f"Phunk #{phunk_id} was flipped by {buyer_short}"

    curated_holdings = get_curated_nfts_holdings(buyer, include_batch=True, curated_contracts=curated_contracts)

    try:
        eth_to_usd = get_latest_eth_price()
        usd_amount = float(price_eth) * eth_to_usd
        sale = {
            'buyer': buyer,
            'seller': seller,
            'eth_amount': float(price_eth),
            'usd_amount': float(usd_amount),
            'transaction_hash': tx_hash,
            'func': function_name,
            'token_id': phunk_id,
        }
        save_sale(sale)
    except Exception as e:
        print(f"issues storing sales: {e}")

    phunk_holdings = get_nft_holdings(wallet_address=buyer,
                                      contract_address=settings.PHUNK_CONTRACT_ADDRESS,
                                      contract_metadata={"name": "CryptoPhunks", "symbol": "PHUNKS",
                                                         "website": "https://www.notlarvalabs.com/"})
    if phunk_holdings:
        current_balance = phunk_holdings.get('balance')
        if current_balance > 1:
            phunk_holdings['balance'] = current_balance - 1
            curated_holdings.append(phunk_holdings)

    ch_tuples = []
    if len(curated_holdings):
        # TODO: sort?
        for curated in curated_holdings:
            name = curated.get('name')
            balance = curated.get('balance')
            symbol = curated.get('symbol')
            ch_tuples.append((symbol, balance))

        ch_text = [f"- {t[1]} {t[0]}" for t in ch_tuples]
        tweet_text += f"\n\n{buyer_short} holds:\n\n"
        tweet_text += "\n".join(ch_text)

    try:
        tweet_text += f"\n\n#{phunk_id} rarity rank: {rankings[phunk_id]} / 10k"
    except Exception as e:
        print(f"problems fetching ranking for phunk id {phunk_id}: {e}")
        tweet_text += "\n"

    tweet_text += f"\nhttps://notlarvalabs.com/market/view/phunk/{phunk_id}"
    print(f"Reply:\n{tweet_text}\n")
    reply(tweet_id=tweet_id, reply_text=tweet_text)

    try:
        if seller == settings.OPENSEA_CONTRACT_ADDRESS:
            floor_token = get_tokens_for_sale(result_size=1)[0]
            floor_price = floor_token.get('floor')

            loss = (floor_price - price_eth) / floor_price

            os_tweet = f"""Another PHUNK sniped via @opensea exploit 🚨

Floor: Ξ{floor_price}
Sold for: Ξ{price_eth} (Ξ-{(floor_price - price_eth):.2f})
Sold % below floor: {loss * 100:.2f}%

PHUNK #{phunk_id}
https://notlarvalabs.com/market/view/phunk/{phunk_id}

{etherscan_link}
"""
            print("\nTweet OS SCAM:")
            print(os_tweet)
    except Exception as e:
        print(f"problems handling opensea hack: {e}")


def handle_tweet(tweet_id, data=None, user=None):
    if not data:
        data = get_tweet(tweet_id).data
        author_id = data.get('author_id')
    else:
        author_id = user.id

    if data.get('in_reply_to_user_id'):
        return

    entities = data.get('entities')
    urls = entities.get('urls')

    if author_id != settings.BOT_TWITTER_ID:
        return

    for url in urls:
        expanded_url = url.get('expanded_url')
        if 'etherscan' in expanded_url:
            hashes = tx_hash_pattern.findall(expanded_url)
            if not hashes or len(hashes) == 0:
                return
            transaction_hash = hashes[0]

            phunk_no_matches = re.compile(r'phunk #(\d+)\b', flags=re.IGNORECASE).findall(data.get('text'))
            phunk_no = int(phunk_no_matches[0])

            handle_transaction(transaction_hash, tweet_id=tweet_id, phunk_id=phunk_no, etherscan_link=expanded_url)

    return data


class PhunkBotListener(tweepy.Stream):

    def on_status(self, status: Status):
        print(f"New streamed tweet: {status.id}")

        json_status = status._json
        handle_tweet(status.id, data=json_status, user=status.user)

    def on_error(self, status_code):
        print(f"Error: {status_code}")
        if status_code == 420:
            # returning False in on_data disconnects the stream
            return False


def start_stream():
    while True:
        try:
            stream = create_stream(stream_cls=PhunkBotListener)
            print("Streaming...")
            stream.filter(follow=[settings.BOT_TWITTER_ID])
        except Exception as e:
            print(f"found error streaming: {e}")
            continue


start_stream()
