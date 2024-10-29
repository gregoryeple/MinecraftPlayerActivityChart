import os
import re
import tarfile
from datetime import datetime

# Set the input folder and output file path
data_folder = '/mnt/data'
output_file_path = '/mnt/data/filtered_logs.txt'

# Define regex pattern for the target log format
log_pattern = r'\[(\d{2}[A-Z]{3}\d{4} \d{2}:\d{2}:\d{2}\.\d{3})\] \[.*\]: (player (joined|left) the game)'

# Open the output file in write mode
with open(output_file_path, 'w') as output_file:
    # Iterate over all files in the data folder
    for filename in os.listdir(data_folder):
        # Check if the file is a .tar.gz archive
        if filename.endswith('.tar.gz'):
            archive_path = os.path.join(data_folder, filename)

            # Open the tar.gz archive
            with tarfile.open(archive_path, 'r:gz') as archive:
                # Iterate through each file in the archive
                for member in archive.getmembers():
                    # Process only regular files (skip folders, etc.)
                    if member.isfile():
                        # Open the file within the archive
                        with archive.extractfile(member) as file:
                            # Read lines from the file
                            for line in file:
                                line = line.decode('utf-8').strip()  # Decode and strip each line

                                # Match the line against the log pattern
                                match = re.match(log_pattern, line)
                                if match:
                                    # Extract date-time and action from the matched pattern
                                    date_str, action = match.groups()

                                    # Convert date format from DDMMMYYYY HH:mm:ss.SSS to DD/MM/YYYY HH:mm:ss
                                    date_obj = datetime.strptime(date_str, '%d%b%Y %H:%M:%S.%f')
                                    formatted_date = date_obj.strftime('%d/%m/%Y %H:%M:%S')

                                    # Write formatted line to output file
                                    output_file.write(f"[{formatted_date}] {action}\n")

print(f"Filtered logs have been saved to {output_file_path}.")
