import asyncio
import time

import requests
from web3 import Web3

import settings
from lib.web3_helpers.common.node import get_contract, get_ens_domain_for_address, decode_contract_transaction
from utils.coinbase import get_latest_eth_price
from utils.nll_marketplace import get_tokens_for_sale
from utils.twitter import tweet


def handle_event(event):
    print(f"event: {event}")
    args = event.get('args')
    phunk_id = args.get('phunkIndex')
    from_ = args.get('fromAddress')

    bidder_ens = get_ens_domain_for_address(from_)
    bidder_short = f"{from_[:6]}...{from_[-4:]}"

    if bidder_ens:
        bidder_short = bidder_ens

    bid_eth_amount = Web3.fromWei(int(args.get('value')), 'ether')

    if bid_eth_amount == 0:
        print("ignoring 0 ETH bid")
        return

    try:
        floor_token = get_tokens_for_sale(result_size=1)[0]
        floor_price = floor_token.get('floor')
        if float(bid_eth_amount) < float(floor_price) * 0.8:
            print(f"too low bid, assume it's spam. floor: {floor_price:.2f} | bid: {bid_eth_amount:.2f}")
            return
    except Exception as e:
        print(f"problem detecting spam bid: {e}")

    transaction_hash = event.get('transactionHash').hex()

    print(f"## Tweeting new PHUNK bid {transaction_hash}...")
    etherscan_url = f"https://etherscan.io/tx/{transaction_hash}"
    nll_url = f"https://www.notlarvalabs.com/cryptophunks/details/{int(phunk_id)}"

    tx_fn, tx_input = decode_contract_transaction(transaction_hash)
    function_name = tx_fn.fn_name
    print(f"function: {function_name}")
    print(f"input: {tx_input}")

    eth_to_usd = get_latest_eth_price()
    price_usd = float(bid_eth_amount) * eth_to_usd

    # TODO: change this?
    metadata_url = f"https://gateway.pinata.cloud/ipfs/QmQcoXyYKokyBHzN3yxDYgPP25cmZkm5Gqp5bzZsTDF7cd/{int(phunk_id)}"
    metadata = requests.get(metadata_url)
    image_url = metadata.json().get('image_url')

    tweet_text = f"""Phunk #{str(phunk_id).zfill(4)} has a new bid of Ξ{bid_eth_amount:.2f} (${price_usd:.2f}) placed by {bidder_short}

{etherscan_url}
{nll_url}
#CryptoPhunks #Phunks #NFTs
"""
    print(tweet_text)
    print("\n\n")

    # TODO: add 'anti-spam' logic here
    tweet(tweet_text, image_urls=[image_url])


async def log_loop(event_filter, poll_interval):
    while True:
        for event in event_filter.get_new_entries():
            handle_event(event)
        await asyncio.sleep(poll_interval)


def main():
    contract = get_contract(settings.MARKETPLACE_CONTRACT_ADDRESS, provider="websocket")
    event_filter = contract.events.PhunkBidEntered.createFilter(fromBlock='latest')
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(
            asyncio.gather(
                log_loop(event_filter, settings.POLLING_TIME_SECONDS)))
    finally:
        loop.close()


if __name__:
    print("Listening to PhunkBidEntered events...")
    exception_count = 0
    while True:
        try:
            main()
        except Exception as e:
            print(f"problems with handling event: {e}")
            exception_count += 1
            time.sleep(60)
            if exception_count > 5:
                raise Exception("too many exceptions, cancelling process!")
            continue
