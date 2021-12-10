import os

from dotenv import load_dotenv

load_dotenv()

TESTING = int(os.getenv("TESTING", 1))

# Contracts
MARKETPLACE_CONTRACT_ADDRESS = "0x3a6aDb264C96258C70681DF32a80dA027baDAB5f"
PHUNK_CONTRACT_ADDRESS = "0xf07468ead8cf26c752c676e43c814fee9c8cf402"
# used to spot transactions exploiting the OpenSea hack
OPENSEA_CONTRACT_ADDRESS = "0x7Be8076f4EA4A4AD08075C2508e481d6C946D12b"

# DB
MONGO_CONN_STRING = os.getenv('MONGO_CONN_STRING')

# Twitter API
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_KEY_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_TOKEN_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

# Misc.
POLLING_TIME_SECONDS = int(os.getenv("BIDS_POLLING_TIME", 30))
# used to fetch Phunks' floor value
CARGO_PROJECT_ID = "60cfe668b0efb10008c3ce10"
# @PhunkBot twitter user ID
BOT_TWITTER_ID = 1411729093033332741


def is_test_mode():
    return TESTING == 1
