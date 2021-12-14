import os

import requests
import tweepy
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import settings

retry_strategy = Retry(
    total=3,
    backoff_factor=2
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)

try:
    auth = tweepy.OAuthHandler(settings.TWITTER_API_KEY, settings.TWITTER_API_KEY_SECRET)
    auth.set_access_token(settings.TWITTER_ACCESS_TOKEN, settings.TWITTER_ACCESS_TOKEN_SECRET)

    twitter_api = tweepy.API(auth)
    twitter_client = tweepy.Client(consumer_key=settings.TWITTER_API_KEY,
                                   consumer_secret=settings.TWITTER_API_KEY_SECRET,
                                   access_token=settings.TWITTER_ACCESS_TOKEN,
                                   access_token_secret=settings.TWITTER_ACCESS_TOKEN_SECRET,
                                   bearer_token=settings.TWITTER_BEARER_TOKEN,
                                   )
except Exception as e:
    print("problems starting Twitter API")


def get_tweet(tweet_id):
    return twitter_client.get_tweet(tweet_id,
                                    expansions=["author_id"],
                                    tweet_fields=["entities", "in_reply_to_user_id"])


def tweet(text, image_urls=None, file_extension="jpg"):
    if settings.is_test_mode():
        print("[test mode, not tweeting]")
        return

    if image_urls:
        media_ids = []
        for index, image_url in enumerate(image_urls):
            image_filename = os.path.join("data", f"phunk_{index}.{file_extension}")
            r = http.get(image_url)
            with open(image_filename, "wb") as f:
                f.write(r.content)

            media = twitter_api.media_upload(image_filename)
            media_ids.append(media.media_id)
            os.remove(image_filename)

        twitter_client.create_tweet(text=text, media_ids=media_ids)
    else:
        twitter_client.create_tweet(text=text)


def create_stream(stream_cls=None):
    if not stream_cls:
        return tweepy.Stream(consumer_key=settings.TWITTER_API_KEY, consumer_secret=settings.TWITTER_API_KEY_SECRET,
                             access_token=settings.TWITTER_ACCESS_TOKEN,
                             access_token_secret=settings.TWITTER_ACCESS_TOKEN_SECRET)
    else:
        return stream_cls(consumer_key=settings.TWITTER_API_KEY, consumer_secret=settings.TWITTER_API_KEY_SECRET,
                          access_token=settings.TWITTER_ACCESS_TOKEN,
                          access_token_secret=settings.TWITTER_ACCESS_TOKEN_SECRET)


def reply(tweet_id, reply_text):
    if settings.is_test_mode():
        print("[test mode, not tweeting]")
        return
    twitter_api.update_status(status=reply_text, in_reply_to_status_id=tweet_id, auto_populate_reply_metadata=True)
