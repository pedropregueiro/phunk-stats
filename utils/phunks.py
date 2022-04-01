import csv
import json
import os

IMAGES_ENDPOINT = "https://phunks.imgix.net/images"

BG_COLOR_MAPPING = {
    "bid": "9957b7",
    "sale": "6A8494"
}

rankings = {}
with open(os.path.join("data", "phunk_rankings.csv"), mode='r') as csv_file:
    csv_reader = csv.DictReader(csv_file)
    for row in csv_reader:
        rankings[int(row.get('id'))] = row.get('ranking')

attributes = {}
with open(os.path.join("data", "all-phunks.json")) as f:
    phunks_raw_data = json.loads(f.read())
    for elem in phunks_raw_data:
        phunk_id = elem.get("data").get("mintNumber")
        attributes[phunk_id] = elem.get("data").get("properties")


def get_phunk_image_url(token_id, kind="sale"):
    token_id = str(int(token_id))  # remove 0s
    bg_color = BG_COLOR_MAPPING.get(kind, BG_COLOR_MAPPING["sale"])
    image_url = f"{IMAGES_ENDPOINT}/phunk{token_id}.png?bg={bg_color}"
    return image_url


def get_phunk_rarity(token_id):
    token_id = int(token_id)  # just in case this is a string
    return rankings[token_id]


def get_phunk_attributes(token_id):
    token_id = int(token_id)
    return attributes[token_id]
