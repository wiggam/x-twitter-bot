from apscheduler.schedulers.blocking import BlockingScheduler
import time
from datetime import datetime, timedelta

from auth import get_twitter_conn_v1, get_twitter_conn_v2
from utils import create_and_post_tweet

# Authenticate to Twitter
client_v1 = get_twitter_conn_v1()
client_v2 = get_twitter_conn_v2()

# List of specific times when you want the tweet to be posted (in Eastern Time)
post_times_et = [(6, 0), (18, 0)]

def job():
    # Get the current time in UTC
    now_utc = datetime.utcnow()

    # Convert UTC time to EST (Eastern Standard Time) by subtracting 5 hours
    now_est = now_utc - timedelta(hours=4)

    print(f"job run at {now_est}")

    # Check if the current time falls within a 1-minute range of any of the post_times_et
    for post_time_hour, post_time_minute in post_times_et:
        if now_est.hour == post_time_hour and  (now_est.minute - post_time_minute) == 1:
            # If it's within the 1-minute range of the specified time, post the tweet
            create_and_post_tweet(client_v1, client_v2)


if __name__ == '__main__':
    # Initialize the scheduler
    scheduler = BlockingScheduler()

    # Schedule the job to run every minute
    scheduler.add_job(job, 'interval', minutes=1)

    # Start the scheduler
    scheduler.start()
