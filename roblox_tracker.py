import json
import os
import time
from datetime import datetime, timezone

import requests

# Configure the Discord webhook outside source control, for example:
#   DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..." python roblox_tracker.py
# Never print the value or commit it to the repository.
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
if not DISCORD_WEBHOOK_URL:
    raise SystemExit("Set the DISCORD_WEBHOOK_URL environment variable before starting.")

CHECK_INTERVAL = 2
STATE_FILE = "roblox_state.json"

GAMES = {
    "The Block": {
        "place_id": 95047916580305,
        "universe_id": 8292068736,
    },
    "Jailbreak": {
        "place_id": 606849621,
        "universe_id": 245662005,
    },
}


if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding="utf-8") as file:
        previous_updates = json.load(file)
else:
    previous_updates = {}


def get_game_data(universe_id):
    response = requests.get(
        "https://games.roblox.com/v1/games",
        params={"universeIds": universe_id},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json().get("data", [])
    if not data:
        raise ValueError("Game not found")
    return data[0]


def send_notification(name, game, updated):
    place_id = game["place_id"]
    universe_id = game["universe_id"]
    embed = {
        "title": f"Roblox Game Updated: {name}",
        "description": (
            f"**{name} has received an update!**\n\n"
            f"**Updated:** {updated}\n"
            f"**Place ID:** `{place_id}`\n"
            f"**Universe ID:** `{universe_id}`\n\n"
            f"[PLAY GAME](https://www.roblox.com/games/{place_id})"
        ),
        "color": 5763719,
        "footer": {"text": "Roblox Update Tracker"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json={"embeds": [embed]},
            timeout=20,
        )
        if not response.ok:
            # Do not raise_for_status(): its exception may include the webhook URL.
            raise RuntimeError(f"Discord webhook request failed (HTTP {response.status_code})")
    except requests.RequestException:
        # Request exceptions can contain the full URL, including its secret token.
        raise RuntimeError("Discord webhook request failed") from None


def save_state():
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(previous_updates, file, indent=4)


def check_games():
    for name, game in GAMES.items():
        try:
            data = get_game_data(game["universe_id"])
            updated = data["updated"]
            previous = previous_updates.get(name)
            print(f"[{datetime.now()}] Checking {name}")

            if previous is None:
                print(f"Initialized tracking for {name}")
            elif previous != updated:
                print(f"UPDATE DETECTED: {name}")
                send_notification(name, game, updated)
                print(f"Notification sent for {name}")

            previous_updates[name] = updated
        except Exception as error:
            # Never include exception details from webhook requests in logs.
            if isinstance(error, RuntimeError) and str(error).startswith("Discord webhook request failed"):
                print(f"Error checking {name}: Discord webhook request failed")
            else:
                print(f"Error checking {name}: {error}")

    save_state()


print("=====================================")
print("       ROBLOX UPDATE TRACKER")
print("=====================================")
print("Monitoring:")
for name, game in GAMES.items():
    print(f"- {name} (Universe: {game['universe_id']})")
print(f"Check interval: {CHECK_INTERVAL} seconds")
print("=====================================")

while True:
    start_time = time.time()
    check_games()
    elapsed = time.time() - start_time
    time.sleep(max(0, CHECK_INTERVAL - elapsed))
