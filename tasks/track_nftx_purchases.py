import asyncio
import logging
import time

from web3 import Web3

import settings
from lib.web3_helpers.common.node import get_transaction, decode_contract_transaction, get_contract
from utils.coinbase import get_latest_eth_price
from utils.phunks import get_phunk_image_url
from utils.twitter import tweet

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def handle_event(event):
    logger.info(f"event: {event}")
    args = event.get('args')
    from_ = args.get('from')
    to_ = args.get('to')
    token_id = args.get('tokenId')

    transaction_hash = event.get('transactionHash').hex()

    if from_.lower() == settings.PHUNK_TOKEN_ADDRESS.lower():
        logger.info(f"## Tweeting NFTX purchase {transaction_hash}...")
        etherscan_url = f"https://etherscan.io/tx/{transaction_hash}"
        transaction = get_transaction(transaction_hash)
        value = transaction.get('value')
        price_eth = Web3.fromWei(int(value), 'ether')

        tx_fn, tx_input = decode_contract_transaction(transaction_hash)
        function_name = tx_fn.fn_name
        if function_name != 'buyAndRedeem':
            logger.warning(f"unexpected nftx vault action: {function_name}")
            return

        amount = tx_input.get('amount', 1)

        # you can buy AMOUNT of phunks so need to divide this
        price_eth = price_eth / amount

        if not price_eth:
            # TODO: sort our NFTX vault price math
            # price_eth = get_nftx_vault_price()
            logger.debug("ignoring transaction due to lack of NFTX floor price")
            return

        eth_to_usd = get_latest_eth_price()
        price_usd = float(price_eth) * eth_to_usd

        image_url = get_phunk_image_url(token_id)

        tweet_text = f"""From the vault (nftx.io) 🥷 🏦

Phunk #{str(token_id).zfill(4)} was flipped for Ξ{price_eth:.2f} (${price_usd:.2f})

{etherscan_url}
#CryptoPhunks #Phunks #NFTs https://notlarvalabs.com/
"""

        logger.info(tweet_text)
        tweet(tweet_text, image_urls=[image_url])


async def log_loop(event_filter, poll_interval):
    while True:
        for event in event_filter.get_new_entries():
            handle_event(event)
        await asyncio.sleep(poll_interval)


def main():
    contract = get_contract(settings.PHUNK_CONTRACT_ADDRESS, provider="websocket")
    event_filter = contract.events.Transfer.createFilter(fromBlock='latest')
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(
            asyncio.gather(
                log_loop(event_filter, settings.POLLING_TIME_SECONDS)))
    finally:
        loop.close()


if __name__:
    logger.info("Listening to Transfer events...")
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
