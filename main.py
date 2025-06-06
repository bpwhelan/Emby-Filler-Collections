import json

import requests
import re
from config import *

def get_anime_data(url):
    """
    Fetches anime filler/canon data from the provided URL.
    Raises an exception for bad HTTP status codes.
    """
    print(f"Fetching anime data from: {url}")
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def get_emby_series_id(series_name):
    """
    Returns the pre-defined PARENT_ID as the series ID.
    This function is modified to bypass searching Emby for the series by name
    since the series ID is already known and provided in PARENT_ID.
    """
    print(f"Using pre-defined Series ID for '{series_name}': {PARENT_ID}")
    return PARENT_ID

def get_emby_episodes(series_id):
    """
    Fetches all episodes for a given series_id from Emby using the provided API structure.
    It recursively queries for all episodes under the series and extracts absolute numbers from their paths or names.
    """
    print(f"Fetching episodes for SeriesId: {series_id}")
    headers = {
        "X-MediaBrowser-Token": EMBY_API_KEY,
        "Content-Type": "application/json",
    }
    # Using the dynamic series_id based on the user's provided API structure
    url = f"{EMBY_SERVER_URL}/emby/Items?Recursive=true&ParentId={series_id}&Fields=Path%2CSortName%2CIndexOptions&EnableUserData=true&api_key={EMBY_API_KEY}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    episodes_data = response.json()

    absolute_num_to_emby_id = {}
    if episodes_data and episodes_data.get("Items"):
        for item in episodes_data["Items"]:
            if item.get("Type") == "Episode": # Ensure we only process actual episodes
                absolute_num = None
                # Attempt to extract absolute number from the file Path (e.g., (005))
                if "Path" in item and item["Path"]:
                    print(item["Path"])
                    match = re.search(r' \((\d+)\) ', item["Path"])
                    if match:
                        absolute_num = int(match.group(1))
                    print(match)
                # If not found in Path, try extracting from the Name
                elif "Name" in item and item["Name"]:
                    match = re.search(r'\((\d+)\)', item["Name"])
                    if match:
                        absolute_num = int(match.group(1))

                if absolute_num:
                    absolute_num_to_emby_id[absolute_num] = item["Id"]
    print(f"Found {len(absolute_num_to_emby_id)} episodes with absolute numbers.")
    return absolute_num_to_emby_id

def create_emby_collection(collection_name, item_emby_ids):
    """
    Creates an Emby collection with the given name and list of Emby item IDs.
    Skips creation if no item IDs are provided.
    """
    if not item_emby_ids:
        print(f"No items to add to collection '{collection_name}'. Skipping creation.")
        return

    print(f"Creating Emby collection: '{collection_name}' with {len(item_emby_ids)} items.")
    headers = {
        "X-MediaBrowser-Token": EMBY_API_KEY,
        "Content-Type": "application/json",
    }
    data = {
        "Name": collection_name,
        "api_key": EMBY_API_KEY,
        # "ParentId": EMBY_USER_ID, # Collections can be created under a user's root
        "IsLocked": False,
        "Ids": ",".join([str(item_id) for item_id in item_emby_ids])
    }
    print(json.dumps(data))
    # print(data)
    # Emby API endpoint for creating collections
    url = f"{EMBY_SERVER_URL}/Collections?api_key={EMBY_API_KEY}"
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status() # Raise an exception for bad status codes
    print(f"Successfully created collection '{collection_name}'.")
    return response.json()

def main():
    global FILLER_EPISODE_NUMBERS
    """
    Main function to orchestrate the process:
    1. Fetches anime data (filler/canon episodes).
    2. Gets the Emby Series ID for the specified anime (now directly from PARENT_ID).
    3. Fetches all episodes from Emby for that series and maps their absolute numbers to Emby IDs.
    4. Filters Emby IDs based on filler/canon lists.
    5. Creates "CANON ONLY" and "FILLER ONLY" collections in Emby.
    """
    try:
        print(FILLER_EPISODE_NUMBERS)
        # 1. Get filler/canon data from the external source
        if FILLER_LIST_URL and not FILLER_EPISODE_NUMBERS:
            data = get_anime_data(FILLER_LIST_URL)
            FILLER_EPISODE_NUMBERS = data.get("fillerEpisodes", [])
        # canon_episode_numbers = set(data.get("cannonEpisodes", []))

        # 3. Get all Emby episodes for the series and map their absolute numbers to Emby IDs
        absolute_num_to_emby_id = get_emby_episodes(PARENT_ID)
        canon_emby_ids = []
        filler_emby_ids = []
        all_emby_ids = []

        if not absolute_num_to_emby_id:
            print(f"No episodes found or no absolute numbers could be extracted from Emby for '{PARENT_ID}'. Exiting.")
            return


        for abs, id in absolute_num_to_emby_id.items():
            if abs in FILLER_EPISODE_NUMBERS:
                filler_emby_ids.append(id)
            else:
                canon_emby_ids.append(id)
            all_emby_ids.append(id)

        # 5. Create Emby collections
        create_emby_collection(f"{SERIES_NAME} - CANON ONLY", canon_emby_ids)
        create_emby_collection(f"{SERIES_NAME} - FILLER ONLY", filler_emby_ids)
        create_emby_collection(f"{SERIES_NAME} - ALL EPISODES", all_emby_ids)

        print("\nScript completed successfully!")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data or connecting to Emby: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
