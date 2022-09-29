import asyncio
import logging
import time
import traceback

from web3 import Web3

import settings
from lib.web3_helpers.common.node import get_contract, get_ens_domain_for_address, decode_contract_transaction, \
    get_transaction
from utils.coinbase import get_latest_eth_price
from utils.nll_marketplace import get_tokens_for_sale
from utils.phunks import get_phunk_image_url, get_phunk_rarity
from utils.twitter import tweet

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def handle_bid(event):
    args = event.get('args')
    phunk_id = args.get('phunkIndex')
    from_ = args.get('fromAddress')

    bidder_ens = get_ens_domain_for_address(from_)
    bidder_short = f"{from_[:6]}...{from_[-4:]}"

    if bidder_ens:
        bidder_short = bidder_ens

    bid_eth_amount = Web3.fromWei(int(args.get('value')), 'ether')

    if bid_eth_amount == 0:
        logger.warning("ignoring 0 ETH bid")
        return

    try:
        floor_token = get_tokens_for_sale(result_size=1)[0]
        floor_price = floor_token.get('floor')
        if float(bid_eth_amount) < float(floor_price) * 0.8:
            logger.info(f"too low bid, assume it's spam. floor: {floor_price:.2f} | bid: {bid_eth_amount:.2f}")
            return
    except Exception as e:
        logger.error(f"problem detecting spam bid: {e}")

    transaction_hash = event.get('transactionHash').hex()

    logger.info(f"## Tweeting new PHUNK bid {transaction_hash}...")
    etherscan_url = f"https://etherscan.io/tx/{transaction_hash}"
    nll_url = f"https://www.notlarvalabs.com/cryptophunks/details/{int(phunk_id)}"

    tx_fn, tx_input = decode_contract_transaction(transaction_hash)
    function_name = tx_fn.fn_name
    logger.debug(f"function: {function_name}")
    logger.debug(f"input: {tx_input}")

    eth_to_usd = get_latest_eth_price()
    price_usd = float(bid_eth_amount) * eth_to_usd

    # TODO: change this?
    image_url = get_phunk_image_url(phunk_id, kind="bid")

    tweet_text = f"""Phunk #{str(phunk_id).zfill(4)} has a new bid of Ξ{bid_eth_amount:.2f} (${price_usd:.2f}) placed by {bidder_short}

{etherscan_url}
{nll_url}
#CryptoPhunks #Phunks #NFTs
    """
    logger.info(tweet_text)

    # TODO: add 'anti-spam' logic here
    tweet(tweet_text, image_urls=[image_url])


def handle_for_sale(event):
    args = event.get('args')
    phunk_id = args.get('phunkIndex')

    for_sale_eth_amount = Web3.fromWei(int(args.get('minValue')), 'ether')
    if for_sale_eth_amount == 0:
        logger.warning("ignoring 0 ETH for sale listing")
        return

    transaction_hash = event.get('transactionHash').hex()

    logger.info(f"## Tweeting new PHUNK sale listing {transaction_hash}...")
    etherscan_url = f"https://etherscan.io/tx/{transaction_hash}"
    nll_url = f"https://www.notlarvalabs.com/cryptophunks/details/{int(phunk_id)}"

    tx = get_transaction(transaction_hash)
    seller = tx.get('from')
    seller_ens = get_ens_domain_for_address(seller)
    seller_short = f"{seller[:6]}...{seller[-4:]}"

    if seller_ens:
        seller_short = seller_ens

    image_url = get_phunk_image_url(phunk_id)

    tweet_text = f"""Phunk #{str(phunk_id).zfill(4)} has been put up for sale for Ξ{for_sale_eth_amount:.2f} by {seller_short}

Rarity: {get_phunk_rarity(phunk_id)} / 10k

{etherscan_url}
{nll_url}
#CryptoPhunks #Phunks #NFTs
"""
    logger.info(tweet_text)

    tweet(tweet_text, image_urls=[image_url])


def handle_event(event):
    logger.info(f"event: {event}")
    event_name = event.get('event')
    if event_name == "PhunkOffered":
        handle_for_sale(event)
    elif event_name == "PhunkBidEntered":
        handle_bid(event)
    else:
        logger.warning(f"ignoring unexpected event: {event_name}")


async def log_loop(event_filter, poll_interval):
    while True:
        for event in event_filter.get_new_entries():
            try:
                handle_event(event)
            except Exception as e:
                logger.error(f"problems handling event: {event}")
                traceback.print_exc()

        await asyncio.sleep(poll_interval)


def main():
    contract = get_contract(settings.MARKETPLACE_CONTRACT_ADDRESS, provider="websocket")
    bid_filter = contract.events.PhunkBidEntered.createFilter(fromBlock='latest')
    for_sale_filter = contract.events.PhunkOffered.createFilter(fromBlock='latest')
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(
            asyncio.gather(
                log_loop(bid_filter, settings.POLLING_TIME_SECONDS),
                log_loop(for_sale_filter, settings.POLLING_TIME_SECONDS)))
    finally:
        loop.close()


if __name__:
    logger.info("Listening to Marketplace events...")
    exception_count = 0
    while True:
        try:
            main()
        except Exception as e:
            logger.error(f"problems with handling event: {e}")
            exception_count += 1
            time.sleep(60)
            if exception_count > 5:
                raise Exception("too many exceptions, cancelling process!")
            continue
