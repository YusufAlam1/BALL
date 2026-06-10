# This script is used for the sportsVU data, to convert JSON files to CSV format

import pandas as pd
import json
import os

data_path = "./data/201601020CHO"
csv_path = "./data"
os.makedirs(csv_path, exist_ok=True)

file = "0021500497.json"
file_path = os.path.join(data_path, file)
game_id = file.replace(".json", "")

with open(file_path, "r") as f:
    data = json.load(f)

moments = []
for event in data["events"]:
    event_id = event["eventId"]
    for moment in event["moments"]:
        game_clock, shot_clock, quarter = moment[2], moment[3], moment[0]
        for player in moment[5]:
            team_id, player_id, x, y, z = player
            moments.append([team_id, player_id, x, y, z, game_clock, shot_clock, quarter, game_id, event_id])

df = pd.DataFrame(moments, columns=["team_id","player_id","x_loc","y_loc","radius","game_clock","shot_clock","quarter","game_id","event_id"])
df.to_csv(f"{csv_path}/{game_id}.csv", index=False)

print(f"Finished {game_id}: {len(df):,} rows")