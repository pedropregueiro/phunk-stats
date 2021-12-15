# UTC times
import argparse
import time

import schedule

from controllers.sniper import fetch_snipable_phunks
from controllers.stats import fetch_phunks_stats, get_aggregated_stats


def set_schedules(run_sniper=False, run_stats=False, run_aggregated=False):
    # Wallets and unique holder info
    if run_stats:
        schedule.every().day.at("05:00").do(fetch_phunks_stats)
        schedule.every().day.at("17:00").do(fetch_phunks_stats)

    # Aggregated sales tweet
    if run_aggregated:
        schedule.every().day.at("16:00").do(get_aggregated_stats)

    # Basic sniping alerts (male/female)
    male_trait = [{'trait_type': 'Sex', 'value': 'Male'}]
    female_trait = [{'trait_type': 'Sex', 'value': 'Female'}]

    if run_sniper:
        schedule.every(120).to(360).minutes.do(fetch_snipable_phunks, filters=male_trait)
        schedule.every(120).to(360).minutes.do(fetch_snipable_phunks, filters=female_trait)

    all_trait_scoops = [
        [{'trait_type': 'Mouth', 'value': 'Medical Mask'}],
        [{'trait_type': 'Neck', 'value': 'Gold Chain'}],
        [{'trait_type': 'Beard', 'value': 'Luxurious Beard'}],
        [{'trait_type': 'Beard', 'value': 'Big Beard'}],
        [{'trait_type': 'Cheeks', 'value': 'Rosy Cheeks'}],
        [{'trait_type': 'Eyes', 'value': 'Green Eye Shadow'}],
        [{'trait_type': 'Eyes', 'value': 'Purple Eye Shadow'}],
        [{'trait_type': 'Eyes', 'value': 'Blue Eye Shadow'}],
        [{'trait_type': 'Eyes', 'value': 'Vr'}],
        [{'trait_type': 'Eyes', 'value': '3D Glasses'}],
        [{'trait_type': 'Eyes', 'value': 'Welding Goggles'}],
        [{'trait_type': 'Face', 'value': 'Spots'}],
        [{'trait_type': 'Teeth', 'value': 'Buck Teeth'}],
        [{'trait_type': 'Hair', 'value': 'Orange Side'}],
        [{'trait_type': 'Hair', 'value': 'Hoodie'}],
        [{'trait_type': 'Hair', 'value': 'Beanie'}],
        [{'trait_type': 'Hair', 'value': 'Half Shaved'}],
        [{'trait_type': 'Hair', 'value': 'Wild White Hair'}],
        [{'trait_type': 'Hair', 'value': 'Top Hat'}],
        [{'trait_type': 'Hair', 'value': 'Cowboy Hat'}],
        [{'trait_type': 'Hair', 'value': 'Red Mohawk'}],
        [{'trait_type': 'Hair', 'value': 'Pink With Hat'}],
        [{'trait_type': 'Hair', 'value': 'Clown Hair Green'}],
        [{'trait_type': 'Nose', 'value': 'Clown Nose'}],
        [{'trait_type': 'Emotion', 'value': 'Smile'}],
        # TODO: need to change Cargo stuff to allow for this
        # [{'trait_type': 'Trait Count', 'value': '1'}],
        # [{'trait_type': 'Trait Count', 'value': '5'}],
    ]

    if run_sniper:
        for scoop in all_trait_scoops:
            schedule.every(120).to(480).minutes.do(fetch_snipable_phunks, filters=scoop, kind='deviation')


if __name__ == '__main__':
    schedule_parser = argparse.ArgumentParser()
    schedule_parser.add_argument('--sniper', action="store_true")
    schedule_parser.add_argument('--stats', action="store_true")
    schedule_parser.add_argument('--aggregated-stats', action="store_true")

    args = schedule_parser.parse_args()
    should_run_sniper = args.sniper
    should_run_stats = args.stats
    should_run_aggregated_stats = args.aggregated_stats

    print(f"should run sniper: {should_run_sniper}")

    set_schedules(run_sniper=should_run_sniper, run_stats=should_run_stats, run_aggregated=should_run_aggregated_stats)

    print("Scheduling all tasks...")
    current_task = None
    while True:
        try:
            schedule.run_pending()
            if not schedule.jobs:
                break
            next_task = min(schedule.jobs)
            if next_task != current_task:
                print(
                    f"Next task scheduled at {next_task.next_run} | "
                    f"task: {next_task.job_func.func.__name__} | "
                    f"args: {next_task.job_func.args} | "
                    f"kwargs: {next_task.job_func.keywords}")
                current_task = next_task
            time.sleep(60)
        except Exception as e:
            print(f"problem with schedule: {e}")
            continue