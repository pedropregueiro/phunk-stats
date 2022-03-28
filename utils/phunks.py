import csv
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


def get_phunk_image_url(token_id, kind="sale"):
    token_id = str(int(token_id))  # remove 0s
    bg_color = BG_COLOR_MAPPING.get(kind, BG_COLOR_MAPPING["sale"])
    image_url = f"{IMAGES_ENDPOINT}/phunk{token_id.zfill(4)}.png?bg={bg_color}"
    return image_url


def get_phunk_rarity(phunk_id):
    phunk_id = int(phunk_id)  # just in case this is a string
    return rankings[phunk_id]
