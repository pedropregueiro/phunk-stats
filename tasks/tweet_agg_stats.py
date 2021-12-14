import time
from datetime import datetime, timezone, timedelta

import schedule

from utils.database import fetch_sales
from utils.twitter import tweet

TOP_SALES_COUNT = 4


def get_aggregated_stats():
    now = datetime.now(timezone.utc)

    filters = {
        "created_at": {
            "$gte": now - timedelta(hours=24),
            "$lt": now
        }
    }
    sales = list(fetch_sales(filters=filters))
    sum_eth = 0
    sum_usd = 0
    top_text = "\n".join(
        [
            f"{index}. #{sale.get('token_id')} for Ξ{sale.get('eth_amount'):.2f} (${sale.get('usd_amount'):,.2f})"
            for index, sale in enumerate(sales[:TOP_SALES_COUNT], start=1)])

    top_images = [f"https://phunks.s3.us-east-2.amazonaws.com/notpunks/notpunk{str(sale.get('token_id')).zfill(4)}.png"
                  for sale in sales[:TOP_SALES_COUNT]]

    for sale in sales:
        sum_eth += sale.get("eth_amount")
        sum_usd += sale.get("usd_amount")

    filters = {
        "created_at": {
            "$gte": now - timedelta(hours=48),
            "$lt": now - timedelta(hours=24),
        }
    }

    previous_24h_sales = list(fetch_sales(filters=filters))
    previous_sum_eth = 0
    previous_sum_usd = 0
    for sale in previous_24h_sales:
        previous_sum_eth += sale.get("eth_amount")
        previous_sum_usd += sale.get("usd_amount")

    eth_diff = sum_eth - previous_sum_eth
    usd_diff = sum_usd - previous_sum_usd

    tweet_text = f"""Last 24h stats 📈
 
# of sales: {len(sales)}
ETH volume: Ξ{sum_eth:.2f} ({f"+Ξ{eth_diff:.2f}" if eth_diff > 0 else f"-Ξ{abs(eth_diff):.2f}"})
USD volume: ${sum_usd:,.2f} ({f"+${usd_diff:,.2f}" if usd_diff > 0 else f"-${abs(usd_diff):,.2f}"})

Top sales:
{top_text} 
"""
    print(tweet_text)
    tweet(tweet_text, image_urls=top_images, file_extension="png")


# UTC times
schedule.every().day.at("16:00").do(get_aggregated_stats)

while True:
    try:
        schedule.run_pending()
        time.sleep(60)
    except Exception as e:
        continue
