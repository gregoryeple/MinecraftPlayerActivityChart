import gzip
import os
import re
from datetime import datetime

# Set the input folder and output file path
DATA_FOLDER = './data'
OUTPUT_FILE = './data/players.txt'

# Define regex pattern for the target log format
LOG_PATTERN = r'\[(\d{2}[A-Za-z]{3}\d{4} \d{2}:\d{2}:\d{2}\.\d{3})\] ?(\[.*\])?:? ?(([a-zA-Z0-9_]{1,20}) (joined|left) the game)'
CRASH_PATTERN = r'\[(\d{2}[A-Za-z]{3}\d{4} \d{2}:\d{2}:\d{2}\.\d{3})\] ?(\[.*\])?:? ?This crash report has been saved to'

# Collect all matching log lines in a list
log_entries = []

# Iterate over all files in the data folder
for filename in os.listdir(DATA_FOLDER):
    # Check if the file is a .tar.gz archive
    if filename.endswith('.gz'):
        archive_path = os.path.join(DATA_FOLDER, filename)

        # Open the tar.gz archive
        with gzip.open(archive_path, 'rt', encoding='utf-8') as archive:
            # Read lines from the file
            for line in archive:
                line = line.strip()  # Decode and strip each line

                # Match the line against the log pattern
                match = re.match(LOG_PATTERN, line)
                if match:
                    # Extract date-time and action from the matched pattern
                    date_str, server_info, player_action, player, action = match.groups()

                    # Convert date format from DDMMMYYYY HH:mm:ss.SSS to DD/MM/YYYY HH:mm:ss
                    date_obj = datetime.strptime(date_str, '%d%b%Y %H:%M:%S.%f')
                    formatted_date = date_obj.strftime('%m/%d/%y %H:%M:%S')
                    log_entries.append((date_obj, player, action, f"[{formatted_date}] {player_action}"))
                else:
                    match = re.match(CRASH_PATTERN, line)
                    if match:
                        # Extract date-time and action from the matched pattern
                        date_str, server_info = match.groups()

                        # Convert date format from DDMMMYYYY HH:mm:ss.SSS to DD/MM/YYYY HH:mm:ss
                        date_obj = datetime.strptime(date_str, '%d%b%Y %H:%M:%S.%f')
                        formatted_date = date_obj.strftime('%m/%d/%y %H:%M:%S')
                        log_entries.append((date_obj, None, None, None))

# Sort log entries by date (first element of each tuple)
log_entries.sort(key=lambda entry: entry[0])

if len(log_entries) > 0:
    with open(OUTPUT_FILE, 'a') as output_file:
        connected_players = []
        for date, player, action, line in log_entries:
            if player is None or action is None or line is None:
                # Handle server crash
                formatted_date = date.strftime('%m/%d/%y %H:%M:%S')
                print(f"[{formatted_date}] Server crashed with {len(connected_players)} player connected")
                for connected_player in connected_players:
                    output_file.write(f"[{formatted_date}] {connected_player} left (server crash)\n")
                connected_players.clear()
            else:
                output_file.write(f"{line}\n")
                if "join" in action and player not in connected_players:
                    connected_players.append(player)
                elif "left" in action and player in connected_players:
                    connected_players.remove(player)

    print(f"{len(log_entries)} actions have been extracted into {OUTPUT_FILE}.")
else:
    print("No data found")