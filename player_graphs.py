import os
import re
from datetime import datetime, time, timedelta
import distinctipy
import tkinter as tk
from io import BytesIO
from tkinter import ttk
import matplotlib.dates as mdates
from matplotlib import pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import pandas as pd
from dateutil import parser as date_parser
from urllib.request import urlopen
from PIL import Image, ImageTk
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

# Constants
DATA_FOLDER = "./data"
CACHE_FOLDER = "./cache"
PLAYER_IMAGE_URL = "https://mc-heads.net/avatar/{}"
TIME_FORMAT = "%d/%m/%Y %H:%M:%S"
DATE_FORMAT = "%d/%m/%Y"
DISPLAY_NAME = "NAME"
DISPLAY_HEAD = "HEAD"
DISPLAY_NAME_AND_HEAD = "BOTH"
GRAPH_BAR_PLAY_TIME = "Total time played"
GRAPH_LINE_PLAYER = "Daily active players"
GRAPH_GANTT_PLAY_TIME = "Play sessions"
GRAPH_STACK_BAR_PLAY_TIME = "Daily play time"
GRAPH_PIE_PLAY_TIME = "Play time distribution"
GRAPH_PIE_PLAY_DAY = "Active days distribution"

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
                    }

                # Track sessions
                if "join" in action.lower():
                    endSession(player_data, player, date)
                    player_data[player]["sessions"].append({"start": date, "end": None})
                elif "left" in action.lower():
                    endSession(player_data, player, date)

                # Update global min and max dates
                min_date = min(min_date, date) if min_date else date
                max_date = max(max_date, date) if max_date else date

    colors = distinctipy.get_colors(len(player_data), pastel_factor = 0.25)
    for i, player in enumerate(player_data):
        player_data[player]["dayPlayed"] = sorted(player_data[player]["dayPlayed"])
        player_data[player]["color"] = colors[i]
        endSession(player_data, player, datetime.now())

    return player_data, min_date, max_date

def endSession(player_data, player, date):
    if player_data[player]["sessions"] and player_data[player]["sessions"][-1]["end"] is None:
        session = player_data[player]["sessions"][-1]
        session["end"] = date
        session["duration"] = (session["end"] - session["start"]).total_seconds() / 60
        player_data[player]["dayPlayed"].add(session["start"].date())
        player_data[player]["dayPlayed"].add(session["end"].date())

def trim_dictionary(data, empty_value):
    # Convert dictionary to list of items (key-value pairs) for ordered processing
    items = list(data.items())
    # Find the first non-empty entry from the start
    start = next((i for i, (_, v) in enumerate(items) if v != empty_value), None)
    # Find the first non-empty entry from the end
    end = next((i for i, (_, v) in enumerate(reversed(items)) if v != empty_value), None)
    # Slice the items list based on the determined start and end indices if there are any non-empty values
    return dict(items[start:len(items) - end]) if start is not None and end is not None else {}

def get_player_image(player):
    image_path = os.path.join(CACHE_FOLDER, f"{player}.png")
    if os.path.exists(image_path):
        return Image.open(image_path)
    try:
        image_url = PLAYER_IMAGE_URL.format(player)
        image_byt = urlopen(image_url).read()
        image = Image.open(BytesIO(image_byt))
        os.makedirs(CACHE_FOLDER, exist_ok = True)
        image.save(image_path, "PNG")
        print(f"Generated cache image for player '{player}'.")
        return image
    except Exception as e:
        print(f"Image for player '{player}' not found.\nError: {e}")
        return None

# Create the main GUI class
class MinecraftStatsApp:
    def __init__(self, root, data, min_date, max_date):
        self.root = root
        self.data = data
        self.min_date = min_date
        self.max_date = max_date
        self.canvas = None

        self.root.title("Minecraft server player stats")

        # Define options for displaying players
        self.display_mode = tk.StringVar(value = DISPLAY_NAME_AND_HEAD)
        self.chart_type = tk.StringVar(value = GRAPH_GANTT_PLAY_TIME)
        self.start_date = tk.StringVar(value = min_date.strftime(DATE_FORMAT))
        self.end_date = tk.StringVar(value = max_date.strftime(DATE_FORMAT))

        self.setup_ui()
        self.update_chart()

    def setup_ui(self):
        # Date range selection
        frame = tk.Frame(self.root)
        frame.pack(pady = 10)

        tk.Label(frame, text = "Start Date:").pack(side = tk.LEFT)
        tk.Entry(frame, textvariable = self.start_date, width = 12).pack(side = tk.LEFT, padx = (0, 10))

        tk.Label(frame, text = "End Date:").pack(side = tk.LEFT)
        tk.Entry(frame, textvariable = self.end_date, width = 12).pack(side=tk.LEFT)

        # Player representation selection
        frame = tk.Frame(self.root)
        frame.pack(pady = 10)
        tk.Radiobutton(frame, text = "Player name", variable = self.display_mode, value = DISPLAY_NAME, command = self.update_chart).pack(side = tk.LEFT)
        tk.Radiobutton(frame, text = "Player head", variable = self.display_mode, value = DISPLAY_HEAD, command = self.update_chart).pack(side = tk.LEFT)
        tk.Radiobutton(frame, text = "Both", variable = self.display_mode, value = DISPLAY_NAME_AND_HEAD, command = self.update_chart).pack(side = tk.LEFT)

        # Chart type selection
        chart_options = [GRAPH_GANTT_PLAY_TIME, GRAPH_LINE_PLAYER, GRAPH_STACK_BAR_PLAY_TIME, GRAPH_BAR_PLAY_TIME, GRAPH_PIE_PLAY_TIME, GRAPH_PIE_PLAY_DAY]
        chart_menu = ttk.Combobox(self.root, textvariable = self.chart_type, values = chart_options)
        chart_menu.pack(pady = 10)
        chart_menu.bind("<<ComboboxSelected>>", lambda event: self.update_chart())

        # Button to refresh chart
        tk.Button(self.root, text = "Update chart", command = self.update_chart).pack(pady = 10)

    def update_chart(self):
        fig = Figure(figsize=(18, 8))
        ax = fig.add_subplot(111)

        # Parse dates for filtering
        try:
            start_date = datetime.combine(datetime.strptime(self.start_date.get(), DATE_FORMAT).date(), time.min)
            end_date = datetime.combine(datetime.strptime(self.end_date.get(), DATE_FORMAT).date(), time.max)
        except ValueError:
            start_date, end_date = self.min_date, self.max_date

        # Filter data by date range
        filtered_data = {
            player: {
                "sessions": [{
                    "start": max(session["start"], start_date),
                    "end": min(session["end"], end_date),
                    "duration": (min(session["end"], end_date) - max(session["start"], start_date)).total_seconds() / 60,
                } for session in info["sessions"] if start_date <= session["start"] <= end_date or start_date <= session["end"] <= end_date],
                "totalPlayed": sum([(min(session["end"], end_date) - max(session["start"], start_date)).total_seconds() / 60 for session in info["sessions"] if start_date <= session["start"] <= end_date or start_date <= session["end"] <= end_date]),
                "dayPlayed": [day for day in info["dayPlayed"] if start_date.date() <= day <= end_date.date()],
                "color": info["color"]
            }
            for player, info in self.data.items()
        }

        # Chart selection logic
        chart_type = self.chart_type.get()
        if chart_type == GRAPH_BAR_PLAY_TIME:
            self.plot_total_time_bar_chart(ax, filtered_data)
        elif chart_type == GRAPH_LINE_PLAYER:
            self.plot_daily_active_players_line_chart(ax, filtered_data)
        elif chart_type == GRAPH_GANTT_PLAY_TIME:
            self.plot_gantt_chart(ax, filtered_data)
        elif chart_type == GRAPH_STACK_BAR_PLAY_TIME:
            self.plot_daily_play_time_stacked_bar_chart(ax, filtered_data)
        elif chart_type == GRAPH_PIE_PLAY_TIME:
            self.plot_total_time_pie_chart(ax, filtered_data)
        elif chart_type == GRAPH_PIE_PLAY_DAY:
            self.plot_active_days_pie_chart(ax, filtered_data)
        else:
            self.show_data_list(filtered_data)
            return  # No plot needed for list

        # Remove old canvas in tkinter
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Canvas):
                widget.destroy()

        # Display canvas in tkinter
        canvas = FigureCanvasTkAgg(fig, self.root)
        canvas.get_tk_widget().pack()
        canvas.draw()

    # Chart plotting methods
    def plot_total_time_bar_chart(self, ax, data):
        players = [player for player in data.keys() if data[player]["totalPlayed"] > 0]
        total_played_hours = [info["totalPlayed"] / 60 for info in data.values() if info["totalPlayed"] > 0]  # Convert minutes to hours

        ax.bar([player + (" " * (8 if self.display_mode.get() == DISPLAY_NAME_AND_HEAD else 0)) for player in players], total_played_hours, color=[data[player]["color"] for player in players])

        for player in players:
            if self.display_mode.get() in [DISPLAY_HEAD, DISPLAY_NAME_AND_HEAD]:
                player_image = get_player_image(player)
                if player_image:
                    ax.add_artist(AnnotationBbox(OffsetImage(player_image, zoom = 0.1), (player + (" " * (8 if self.display_mode.get() == DISPLAY_NAME_AND_HEAD else 0)), 0), frameon = False, box_alignment = (0.5, 1.5)))

        if self.display_mode.get() == DISPLAY_HEAD:
            for label in ax.get_xticklabels():
                label.set_color(plt.matplotlib.colors.to_rgba("white", 0))

        ax.set_title("Time played by player")
        ax.set_xlabel("Players")
        ax.set_ylabel("Time played (hours)")
        ax.tick_params(axis = 'x', rotation = 45 if self.display_mode.get() == DISPLAY_NAME else 90)

    def plot_daily_active_players_line_chart(self, ax, data):
        all_dates = pd.date_range(self.min_date, self.max_date)
        daily_active_counts = {date.date(): 0 for date in all_dates}

        for info in data.values():
            for day in info["dayPlayed"]:
                if day in daily_active_counts.keys():
                    daily_active_counts[day] += 1

        daily_active_counts = trim_dictionary(daily_active_counts, 0)
        dates = list(daily_active_counts.keys())
        active_counts = list(daily_active_counts.values())

        ax.plot(dates, active_counts, color="blue", alpha=0.7)
        ax.fill_between(dates, active_counts, color="lightblue", alpha=0.5)
        ax.scatter(dates, active_counts, color="blue", s=50, label="Player count")
        ax.set_title("Daily active players")
        ax.set_xlabel("Date")
        ax.set_ylabel("Number of active players")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%y"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.tick_params(axis = 'x', rotation = 45)

    def plot_gantt_chart(self, ax, data):
        dates = pd.date_range(min([min(info["dayPlayed"]) for info in data.values() if info["dayPlayed"]]), (max([max(info["dayPlayed"]) for info in data.values() if info["dayPlayed"]]) + timedelta(days = 1)))

        for i, (player, info) in enumerate([(player, info) for (player, info) in data.items() if info["sessions"]]):
            if self.display_mode.get() in [DISPLAY_HEAD, DISPLAY_NAME_AND_HEAD]:
                player_image = get_player_image(player)
                if player_image:
                    ax.add_artist(AnnotationBbox(OffsetImage(player_image, zoom = 0.1), (min(dates), i), frameon = False, box_alignment = (1.5, 0.5)))
            for session in info["sessions"]:
                ax.barh(player + (' ' * (8 if self.display_mode.get() == DISPLAY_NAME_AND_HEAD else 0)), (session["end"] - session["start"]).total_seconds() / (60 * 60 * 24), left = session["start"], color = info["color"])

        for date in dates:
            ax.axvline(date, color = "gray", linestyle = "-", linewidth = 0.5)

        if self.display_mode.get() == DISPLAY_HEAD:
            for label in ax.get_yticklabels():
                label.set_color(plt.matplotlib.colors.to_rgba("white", 0))

        ax.set_title("Play sessions")
        ax.set_xlabel("Date")
        ax.set_ylabel("Players")
        ax.set_xlim(min(dates), max(dates))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%y"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.tick_params(axis='x', rotation=45)

    def plot_daily_play_time_stacked_bar_chart(self, ax, data):
        all_dates = pd.date_range(min([min(info["dayPlayed"]) for info in data.values() if info["dayPlayed"]]), max([max(info["dayPlayed"]) for info in data.values() if info["dayPlayed"]]))
        daily_play_times = {player: [0] * len(all_dates) for player in data.keys() if data[player]["sessions"]}

        for i, date in enumerate(all_dates):
            for player, info in data.items():
                if player in daily_play_times:
                    daily_play_times[player][i] += sum((session["end"] - session["start"]).total_seconds() / 3600 for session in info["sessions"] if session["start"].date() == date.date())

        dates = list(all_dates)
        bottom = np.zeros(len(dates))
        for player, play_times in daily_play_times.items():
            # A space is added because labels starting with an underscore are not shown
            ax.bar(dates, play_times, bottom = bottom, label = rf" {player}", color = data[player]["color"])
            bottom += np.array(play_times)

        ax.set_title("Daily play time")
        ax.set_xlabel("Date")
        ax.set_ylabel("Total play time (hours)")
        ax.legend()
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%y"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.tick_params(axis='x', rotation=45)

    def plot_total_time_pie_chart(self, ax, data):
        players = [player for player in data.keys() if data[player]["totalPlayed"] > 0]
        total_played_hours = [info["totalPlayed"] / 60 for info in data.values() if info["totalPlayed"] > 0]  # Convert minutes to hours

        ax.set_title("Play time distribution")
        wedges, texts, junk = ax.pie(total_played_hours, labels = players if self.display_mode.get() == DISPLAY_NAME else [("" if self.display_mode.get() == DISPLAY_HEAD else ((" " * 4) + player + (" " * 4))) for player in players], autopct = (lambda val: str(round(val / 100 * sum(total_played_hours))) + "H"), startangle = 90, colors = [data[player]["color"] for player in players])
        # Add images next to each label
        if self.display_mode.get() in [DISPLAY_HEAD, DISPLAY_NAME_AND_HEAD]:
            for i, player in enumerate(players):
                player_image = get_player_image(player)
                if player_image:
                    # Calculate position for annotation based on wedge angle
                    angle = (wedges[i].theta2 - wedges[i].theta1) / 2. + wedges[i].theta1
                    x = np.cos(np.radians(angle)) * 1.1
                    y = np.sin(np.radians(angle)) * 1.1
                    # Add image next to label
                    ab = AnnotationBbox(OffsetImage(player_image, zoom = 0.1), (x, y), frameon = False, box_alignment = (0.5, 0.5))
                    ax.add_artist(ab)

    def plot_active_days_pie_chart(self, ax, data):
        players = [player for player in data.keys() if data[player]["dayPlayed"]]
        active_days_count = [len(info["dayPlayed"]) for info in data.values() if info["dayPlayed"]]

        ax.set_title("Active days distribution")
        wedges, texts, junk = ax.pie(active_days_count, labels = players if self.display_mode.get() == DISPLAY_NAME else [("" if self.display_mode.get() == DISPLAY_HEAD else ((" " * 4) + player + (" " * 4))) for player in players], autopct = (lambda val: round(val / 100 * sum(active_days_count))), startangle = 90, colors = [data[player]["color"] for player in players])
        # Add images next to each label
        if self.display_mode.get() in [DISPLAY_HEAD, DISPLAY_NAME_AND_HEAD]:
            for i, player in enumerate(players):
                player_image = get_player_image(player)
                if player_image:
                    # Calculate position for annotation based on wedge angle
                    angle = (wedges[i].theta2 - wedges[i].theta1) / 2. + wedges[i].theta1
                    x = np.cos(np.radians(angle)) * 1.1
                    y = np.sin(np.radians(angle)) * 1.1
                    # Add image next to label
                    ab = AnnotationBbox(OffsetImage(player_image, zoom = 0.1), (x, y), frameon = False, box_alignment = (0.5, 0.5))
                    ax.add_artist(ab)

    def show_data_list(self, data):
        list_window = tk.Toplevel(self.root)
        list_window.title("Player Data List")

        for player, info in data.items():
            player_label = tk.Label(list_window, text=f"{player}:", font=("Arial", 10, "bold"))
            player_label.pack(anchor="w")

            sessions_text = "\n".join([f"  Start: {s['start']}, End: {s['end']}" for s in info["sessions"]])
            details = (
                f"First Seen: {info['firstSeen']}\n"
                f"Last Seen: {info['lastSeen']}\n"
                f"Total Played: {info['totalPlayed'] / 60:.2f} hours\n"
                f"Days Played: {', '.join([d.strftime(DATE_FORMAT) for d in info['dayPlayed']])}\n"
                f"Sessions:\n{sessions_text}\n"
            )
            details_label = tk.Label(list_window, text=details, justify="left", font=("Arial", 9))
            details_label.pack(anchor="w", padx=20)


# Run the app
if __name__ == "__main__":
    data, min_date, max_date = parse_data()
    root = tk.Tk()
    app = MinecraftStatsApp(root, data, min_date, max_date)
    root.mainloop()
