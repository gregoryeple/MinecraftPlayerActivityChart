import os
import re
from datetime import datetime
import tkinter as tk
from io import BytesIO
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
from dateutil import parser as date_parser
from urllib.request import urlopen
from PIL import Image, ImageTk

# Constants
DATA_FOLDER = "./data"
PLAYER_IMAGE_URL = "https://mc-heads.net/avatar/{}"
TIME_FORMAT = "%d/%m/%Y %H:%M:%S"
DATE_FORMAT = "%d/%m/%Y"


# Parse and organize player data from files
def parse_data():
    player_data = {}
    min_date, max_date = None, None

    for filename in os.listdir(DATA_FOLDER):
        filepath = os.path.join(DATA_FOLDER, filename)
        with open(filepath, "r") as file:
            for line in file:
                match = re.match(r"\[(.*?)\] (\S+) (joined|left)", line)
                if not match:
                    continue
                timestamp, player, action = match.groups()
                date = date_parser.parse(timestamp)

                # Initialize player in dictionary if not exists
                if player not in player_data:
                    player_data[player] = {
                        "sessions": [],
                        "dayPlayed": set(),
                        "firstSeen": date,
                        "lastSeen": date,
                        "totalPlayed": 0.0
                    }
                # Update first and last seen dates
                player_data[player]["firstSeen"] = min(player_data[player]["firstSeen"], date)
                player_data[player]["lastSeen"] = max(player_data[player]["lastSeen"], date)

                # Track sessions
                if action == "joined":
                    player_data[player]["sessions"].append({"start": date, "end": None})
                elif action == "left" and player_data[player]["sessions"] and player_data[player]["sessions"][-1]["end"] is None:
                    session = player_data[player]["sessions"][-1]
                    session["end"] = date
                    duration = (session["end"] - session["start"]).total_seconds() / 60  # in minutes
                    player_data[player]["totalPlayed"] += duration
                    player_data[player]["dayPlayed"].add(session["start"].date())
                    player_data[player]["dayPlayed"].add(session["end"].date())

                # Update global min and max dates
                min_date = min(min_date, date) if min_date else date
                max_date = max(max_date, date) if max_date else date

    for player in player_data:
        player_data[player]["dayPlayed"] = sorted(player_data[player]["dayPlayed"])
    print(player_data)
    return player_data, min_date, max_date


# Create the main GUI class
class MinecraftStatsApp:
    def __init__(self, root, data, min_date, max_date):
        self.root = root
        self.data = data
        self.min_date = min_date
        self.max_date = max_date

        self.root.title("Minecraft Server Player Stats")

        # Define options for displaying players
        self.display_mode = tk.StringVar(value="name")
        self.chart_type = tk.StringVar(value="bar")
        self.start_date = tk.StringVar(value=min_date.strftime(DATE_FORMAT))
        self.end_date = tk.StringVar(value=max_date.strftime(DATE_FORMAT))

        self.setup_ui()
        self.update_chart()

    def setup_ui(self):
        # Date range selection
        frame = tk.Frame(self.root)
        frame.pack(pady=10)

        tk.Label(frame, text="Start Date:").pack(side=tk.LEFT)
        tk.Entry(frame, textvariable=self.start_date, width=12).pack(side=tk.LEFT)

        tk.Label(frame, text="End Date:").pack(side=tk.LEFT)
        tk.Entry(frame, textvariable=self.end_date, width=12).pack(side=tk.LEFT)

        # Player representation selection
        tk.Radiobutton(self.root, text="Player Name", variable=self.display_mode, value="name").pack()
        tk.Radiobutton(self.root, text="Player Image", variable=self.display_mode, value="image").pack()
        tk.Radiobutton(self.root, text="Both", variable=self.display_mode, value="both").pack()

        # Chart type selection
        chart_options = ["bar", "line", "gantt", "stacked_bar", "pie_total", "pie_days", "list"]
        chart_menu = ttk.Combobox(self.root, textvariable=self.chart_type, values=chart_options)
        chart_menu.pack(pady=10)

        # Button to refresh chart
        tk.Button(self.root, text="Update Chart", command=self.update_chart).pack()

    def get_player_image(self, player):
        try:
            image_url = PLAYER_IMAGE_URL.format(player)
            image_byt = urlopen(image_url).read()
            image = Image.open(BytesIO(image_byt))
            image.thumbnail((32, 32))
            return ImageTk.PhotoImage(image)
        except:
            return None

    def update_chart(self):
        fig = Figure(figsize=(8, 6))
        ax = fig.add_subplot(111)

        # Parse dates for filtering
        try:
            start_date = datetime.strptime(self.start_date.get(), DATE_FORMAT)
            end_date = datetime.strptime(self.end_date.get(), DATE_FORMAT)
        except ValueError:
            start_date, end_date = self.min_date, self.max_date

        # Apply filtering logic on data and draw selected chart type
        # Placeholder for chart plotting logic based on self.chart_type.get()

        # Display figure in tkinter
        canvas = FigureCanvasTkAgg(fig, self.root)
        canvas.get_tk_widget().pack()
        canvas.draw()


# Run the app
if __name__ == "__main__":
    data, min_date, max_date = parse_data()
    root = tk.Tk()
    app = MinecraftStatsApp(root, data, min_date, max_date)
    root.mainloop()
