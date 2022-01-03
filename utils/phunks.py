import csv
import os

IMAGE_S3_BUCKET = "https://phunks.s3.us-east-2.amazonaws.com/notpunks"

rankings = {}
with open(os.path.join("data", "phunk_rankings.csv"), mode='r') as csv_file:
    csv_reader = csv.DictReader(csv_file)
    for row in csv_reader:
        rankings[int(row.get('id'))] = row.get('ranking')


def get_phunk_image_url(token_id):
    token_id = str(int(token_id))  # remove 0s
    image_url = f"{IMAGE_S3_BUCKET}/notpunk{token_id.zfill(4)}.png"
    return image_url


def get_phunk_rarity(phunk_id):
    phunk_id = int(phunk_id)  # just in case this is a string
    return rankings[phunk_id]
