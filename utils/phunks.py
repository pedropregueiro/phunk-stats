IMAGE_S3_BUCKET = "https://phunks.s3.us-east-2.amazonaws.com/notpunks"


def get_phunk_image_url(token_id):
    token_id = str(int(token_id))  # remove 0s
    image_url = f"{IMAGE_S3_BUCKET}/notpunk{token_id.zfill(4)}.png"
    return image_url
