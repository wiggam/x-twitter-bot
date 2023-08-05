import os
import sqlite3
import requests
import tweepy
from keys import google_key, cx

# Assuming utils.py is inside the app folder
APP_DIR = os.path.dirname(__file__)

# Path to the tweet counter file (inside the /app directory)
TWEET_COUNTER_FILE = os.path.join(APP_DIR, "tweet_counter.txt")

# Path to the SQLite database file (inside the /app directory)
DB_FILE_PATH = os.path.join(APP_DIR, "my_database.db")

# Path to the jpg file (inside the /app directory)
TEMP_IMAGE_DIR = os.path.join(APP_DIR, "temp_image.jpg")

# Path to Tweet Order Dict txt file (inside the /app directory)
TWEET_ORDER_DICT = os.path.join(APP_DIR, "tweet_order_dict.txt")

def create_image_link(search, attempt):

    base_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": google_key,
        "cx": cx,
        "q": search,
        "num": attempt,
        "searchType": 'image'
    }

    response = requests.get(base_url, params=params)
    data = response.json()

    index = attempt - 1

    if 'items' in data:
        items_dict = data['items'][index]
        if items_dict['link']:
            return items_dict['link']
        elif items_dict['image']:
            image_dict = items_dict['image']
            return image_dict['contextLink']
        else: 
            print("No image link")
    elif 'error' in data:
        print(data['error'])
    else:
        print("No 'ITEMS' in JSON response")


def save_api_requests():
    return "https://www.christies.com/img/LotImages/2006/NYR/2006_NYR_01717_0118_000(125845).jpg?mode=max"


def get_search(id):
    # Connect to the SQLite database
    conn = sqlite3.connect(DB_FILE_PATH)

    try:
        # Query the database to get the search
        cursor = conn.cursor()
        cursor.execute("SELECT art_title, artist FROM tweets WHERE id=?", (id,))
        row_data = cursor.fetchone()
        art_title = row_data[0]
        artist = row_data[1]
        search = f"{art_title} by {artist}"
        return search

    except sqlite3.Error as e:
        print("Error occurred while querying the database:", e)
        return None

    finally:
        # Close the connection to the database
        conn.close()


def fetch_tweet_data(id):
    # Connect to the SQLite database
    conn = sqlite3.connect(DB_FILE_PATH)

    try:
        # Query the database to get the tweet data based on the id
        cursor = conn.cursor()
        cursor.execute("SELECT art_title, artist, year, description FROM tweets WHERE id=?", (id,))
        row_data = cursor.fetchone()

        if row_data:
            # Convert the row data to a dictionary
            tweet_data = {
                'art_title': row_data[0],
                'artist': row_data[1],
                'year': row_data[2],
                'description': row_data[3]
            }
            return tweet_data
        else:
            print(f"No data found for id: {id}.")
            return None

    except sqlite3.Error as e:
        print("Error occurred while querying the database:", e)
        return None

    finally:
        # Close the connection to the database
        conn.close()

def load_tweet_order_dict(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return {int(k): int(v) for k, v in [line.strip().split(',') for line in file]}
    else:
        return {}

def create_and_post_tweet(client_v1, client_v2):
    max_attempts = 7

    # Load the tweet order dictionary from the file
    tweet_order_dict = load_tweet_order_dict(TWEET_ORDER_DICT)

    # Read the current tweet counter from the file
    if os.path.exists(TWEET_COUNTER_FILE):
        with open(TWEET_COUNTER_FILE, "r") as counter_file:
            tweet_counter = int(counter_file.read())
    else:
        tweet_counter = 1  # Start with 1 if the file doesn't exist

    while tweet_counter:
        # Fetch tweet data based on the current tweet counter from the tweet_order_dict
        tweet_id = tweet_order_dict[tweet_counter]
        tweet_data = fetch_tweet_data(tweet_id)
        if tweet_data is None:
            print("No more tweets to post.")
            return

        art_title = tweet_data['art_title']
        artist = tweet_data['artist']
        year = tweet_data['year']
        description = tweet_data['description']

        # Check if tweet_text needs to be split into multiple tweets
        tweet_text = f"{art_title} by {artist}\nDate: {year}\n\n{description}"
        desc = None
        if len(tweet_text) > 280:
            tweet_text1 = f"{art_title} by {artist}\n\nDate: {year}"
            desc = f"{description}"

        attempt = 1
        search = get_search(tweet_id)
        image_link = create_image_link(search, attempt)

        # Download the image from the image link
        while attempt <= max_attempts:
            try:
                response = requests.get(image_link)
                response.raise_for_status()

                # Save the image to a local file (e.g., 'temp_image.jpg')
                with open(TEMP_IMAGE_DIR, 'wb') as f:
                    f.write(response.content)

                media_path = TEMP_IMAGE_DIR
                media = client_v1.simple_upload(filename=media_path)
                media_id = media.media_id

                # Post the tweet with the image and tweet_text
                if desc is not None:
                    tweet = client_v2.create_tweet(media_ids=[media_id], text=tweet_text1)
                    client_v2.create_tweet(text=desc, in_reply_to_tweet_id=tweet.data['id'])
                else: 
                    client_v2.create_tweet(text=tweet_text, media_ids=[media_id])

                print(f"Success - Tweet Number: {tweet_counter}, Tweet ID: {tweet_id}, Title: {search}, has been posted")

                # Delete the image file after tweeting
                os.remove(TEMP_IMAGE_DIR)

                # Increment the tweet counter
                tweet_counter += 1

                # Check if the tweet counter has reached the maximum value
                if tweet_counter > len(tweet_order_dict):
                    # If so, reset the tweet counter to 1 and save the current tweet ID to the file
                    tweet_counter = 1
                    with open(TWEET_COUNTER_FILE, "w") as counter_file:
                        counter_file.write(str(tweet_counter))

                else:
                    # Save the updated tweet counter to the file
                    with open(TWEET_COUNTER_FILE, "w") as counter_file:
                        counter_file.write(str(tweet_counter))

                return           
        
            except Exception as e:
                # Exception occurred while downloading image or uploading media
                print(f"Error: {e}")
                if os.path.exists(TEMP_IMAGE_DIR):
                    os.remove(TEMP_IMAGE_DIR)  # Remove the invalid image file

                print(f"Attempt {attempt} of 7 failed for Tweet Number: {tweet_counter} - Tweet ID: {tweet_id}, generating new image")

                # Attempt to generate a new image link and continue with the next attempt
                attempt += 1
                image_link = create_image_link(search, attempt)

        else:
            print(f"Maximum attempts ({max_attempts}) reached for tweet {tweet_counter}.")
            tweet_counter += 1  # Move to the next tweet and attempt to post it
        
            # Save the updated tweet counter to the file
            with open(TWEET_COUNTER_FILE, "w") as counter_file:
                counter_file.write(str(tweet_counter))
