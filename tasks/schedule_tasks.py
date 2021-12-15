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
    male_trait = [{'key': 'Sex', 'value': 'Male'}]
    female_trait = [{'key': 'Sex', 'value': 'Female'}]

    if run_sniper:
        schedule.every(120).to(360).minutes.do(fetch_snipable_phunks, filters=male_trait)
        schedule.every(120).to(360).minutes.do(fetch_snipable_phunks, filters=female_trait)

    all_trait_scoops = [
        [{'key': 'Mouth', 'value': 'Medical Mask'}],
        [{'key': 'Neck', 'value': 'Gold Chain'}],
        [{'key': 'Beard', 'value': 'Luxurious Beard'}],
        [{'key': 'Beard', 'value': 'Big Beard'}],
        [{'key': 'Cheeks', 'value': 'Rosy Cheeks'}],
        [{'key': 'Eyes', 'value': 'Green Eye Shadow'}],
        [{'key': 'Eyes', 'value': 'Purple Eye Shadow'}],
        [{'key': 'Eyes', 'value': 'Blue Eye Shadow'}],
        [{'key': 'Eyes', 'value': 'Vr'}],
        [{'key': 'Eyes', 'value': '3D Glasses'}],
        [{'key': 'Eyes', 'value': 'Welding Goggles'}],
        [{'key': 'Face', 'value': 'Spots'}],
        [{'key': 'Teeth', 'value': 'Buck Teeth'}],
        [{'key': 'Hair', 'value': 'Orange Side'}],
        [{'key': 'Hair', 'value': 'Hoodie'}],
        [{'key': 'Hair', 'value': 'Beanie'}],
        [{'key': 'Hair', 'value': 'Half Shaved'}],
        [{'key': 'Hair', 'value': 'Wild White Hair'}],
        [{'key': 'Hair', 'value': 'Top Hat'}],
        [{'key': 'Hair', 'value': 'Cowboy Hat'}],
        [{'key': 'Hair', 'value': 'Red Mohawk'}],
        [{'key': 'Hair', 'value': 'Pink With Hat'}],
        [{'key': 'Hair', 'value': 'Clown Hair Green'}],
        [{'key': 'Nose', 'value': 'Clown Nose'}],
        [{'key': 'Emotion', 'value': 'Smile'}],
        # TODO: need to change Cargo stuff to allow for this
        # [{'key': 'Trait Count', 'value': '1'}],
        # [{'key': 'Trait Count', 'value': '5'}],
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
