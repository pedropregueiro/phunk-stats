from datetime import datetime, timezone

import pymongo

import settings

mongo_client = pymongo.MongoClient(settings.MONGO_CONN_STRING)

sales_coll = mongo_client['phunks']['sales']
holders_coll = mongo_client['phunks']['holders']
stats_coll = mongo_client['phunks']['stats']
rarity_tweets_coll = mongo_client['phunks']['rarity_tweets']


def save_sale(sale_data):
    sale_data['created_at'] = datetime.now(timezone.utc)
    inserted = sales_coll.insert_one(sale_data)
    return inserted.inserted_id


def fetch_sales(filters=None):
    return sales_coll.find(filter=filters, sort=[("eth_amount", pymongo.DESCENDING)])


def save_holder(holder_data):
    holder_data['created_at'] = datetime.now(timezone.utc)
    inserted = holders_coll.insert_one(holder_data)
    return inserted.inserted_id


def get_holder(holder_id):
    return holders_coll.find_one({'_id': holder_id})


def delete_holder(holder_id):
    holders_coll.delete_one({'_id': holder_id})


def update_holder(holder_id, update_data):
    update_data['updated_at'] = datetime.now(timezone.utc)
    holders_coll.update_one({'_id': holder_id}, {"$set": update_data})


def save_stats(stats_data):
    stats_data['created_at'] = datetime.now(timezone.utc)
    inserted = stats_coll.insert_one(stats_data)
    return inserted.inserted_id


def get_latest_stats():
    return stats_coll.find_one(sort=[("created_at", pymongo.DESCENDING)])


def save_latest_rarity_tweet(tweet_data):
    tweet_data['created_at'] = datetime.now(timezone.utc)
    inserted = rarity_tweets_coll.insert_one(tweet_data)
    return inserted.inserted_id


def get_latest_rarity_tweet(trait_name=None, trait_value=None):
    return rarity_tweets_coll.find_one(filter={"trait_name": trait_name, "trait_value": trait_value},
                                       sort=[("created_at", pymongo.DESCENDING)])
