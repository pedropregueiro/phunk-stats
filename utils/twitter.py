import os

import requests
import tweepy
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

API_KEY = os.environ.get('TWITTER_API_KEY')
API_KEY_SECRET = os.environ.get('TWITTER_API_SECRET')
ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_SECRET')
BEARER_TOKEN = os.environ.get('TWITTER_BEARER_TOKEN')

retry_strategy = Retry(
    total=3,
    backoff_factor=2
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)
http.mount("http://", adapter)

try:
    auth = tweepy.OAuthHandler(API_KEY, API_KEY_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

    twitter_api = tweepy.API(auth)
    twitter_client = tweepy.Client(consumer_key=API_KEY,
                                   consumer_secret=API_KEY_SECRET,
                                   access_token=ACCESS_TOKEN,
                                   access_token_secret=ACCESS_TOKEN_SECRET,
                                   bearer_token=BEARER_TOKEN,
                                   )
except Exception as e:
    print("problems starting Twitter API")


def get_tweet(tweet_id):
    return twitter_client.get_tweet(tweet_id,
                                    expansions=["author_id"],
                                    tweet_fields=["entities", "in_reply_to_user_id"])


def tweet(text, image_url=None):
    media_id = None

    if image_url:
        image_filename = "phunk.jpg"
        r = http.get(image_url)
        with open(image_filename, "wb") as f:
            f.write(r.content)

        media = twitter_api.media_upload(image_filename)
        media_id = media.media_id

        twitter_client.create_tweet(text=text, media_ids=[media_id])
    else:
        twitter_client.create_tweet(text=text)


def create_stream(stream_cls=None):
    if not stream_cls:
        return tweepy.Stream(consumer_key=API_KEY, consumer_secret=API_KEY_SECRET,
                             access_token=ACCESS_TOKEN, access_token_secret=ACCESS_TOKEN_SECRET)
    else:
        return stream_cls(consumer_key=API_KEY, consumer_secret=API_KEY_SECRET,
                          access_token=ACCESS_TOKEN, access_token_secret=ACCESS_TOKEN_SECRET)


def reply(tweet_id, reply_text):
    twitter_api.update_status(status=reply_text, in_reply_to_status_id=tweet_id, auto_populate_reply_metadata=True)
