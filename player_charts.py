import os
import re
from datetime import datetime, time, timedelta
from math import floor

import distinctipy
import tkinter as tk
from io import BytesIO
from tkinter import ttk
from tkcalendar import DateEntry
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
GRAPH_LINE_PLAYER_HOUR = "Hourly active players"
GRAPH_LINE_PLAYER_DAY = "Daily active players"
GRAPH_GANTT_PLAY_TIME = "Play sessions"
GRAPH_GANTT_PLAY_DAY = "Active days"
GRAPH_STACK_BAR_PLAY_TIME = "Daily play time"
GRAPH_PIE_PLAY_TIME = "Play time distribution"
GRAPH_PIE_PLAY_DAY = "Active days distribution"
SORT_NAME = "NAME"
SORT_PLAY_FIRST = "FIRST"
SORT_PLAY_LAST = "LAST"
SORT_PLAY_TIME = "TIME"
SORT_PLAY_DAY = "DAY"
FILTER_TIME_PLAYED = "Time played (in hours)"
FILTER_DAY_PLAYED = "Day played"

# Parse and organize player data from files
def parse_data():
    player_data = {}
    min_date, max_date = None, None

    for filename in os.listdir(DATA_FOLDER):
        filepath = os.path.join(DATA_FOLDER, filename)
        if os.path.isfile(filepath) and not filepath.endswith(('.zip', '.tar', '.tar.gz', '.gz', '.rar')):
            with open(filepath, "r") as file:
                for line in file:
                    match = re.match(r"\[(.*?)\] ([a-zA-Z0-9_]{1,20}) (joined|left)", line)
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
        if player_data[player]["sessions"]:
            player_data[player]["sessions"] = sorted(player_data[player]["sessions"], key = lambda session: session["start"])

    return player_data, min_date, max_date

def endSession(player_data, player, date):
    if player_data[player]["sessions"] and player_data[player]["sessions"][-1]["end"] is None:
        session = player_data[player]["sessions"][-1]
        session["end"] = date
        session["duration"] = (session["end"] - session["start"]).total_seconds() / 60
        player_data[player]["dayPlayed"].add(session["start"].date())
        player_data[player]["dayPlayed"].add(session["end"].date())

def format_datetime(datestr, timeofday = None, defaultdate = datetime.now()):
    try:
        return datetime.combine(datetime.strptime(datestr, DATE_FORMAT).date(), timeofday) if timeofday else datetime.strptime(datestr, DATE_FORMAT)
    except ValueError:
        return defaultdate

def format_number(numstr, defaultvalue = 0):
    try:
       return float(numstr)
    except ValueError:
        return defaultvalue


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
        self.start_date = tk.StringVar(value = max(min_date, (max_date - timedelta(days = 28)).replace(day = 1)).strftime(DATE_FORMAT))
        self.end_date = tk.StringVar(value = max_date.strftime(DATE_FORMAT))
        self.chart_type = tk.StringVar(value = GRAPH_GANTT_PLAY_TIME if ((max_date.date() - max(min_date, (max_date - timedelta(days = 28)).replace(day = 1)).date()).days < 30) else GRAPH_GANTT_PLAY_DAY)
        self.display_mode = tk.StringVar(value = DISPLAY_NAME_AND_HEAD)
        self.sort_mode = tk.StringVar(value = SORT_NAME)
        self.sort_reverse = tk.BooleanVar(value = False)
        self.filter_type = tk.StringVar(value = FILTER_TIME_PLAYED)
        self.filter_min = tk.StringVar(value = "")
        self.filter_max = tk.StringVar(value = "")

        self.setup_ui()
        self.update_chart()

    def setup_ui(self):
        # Date range selection
        frame = tk.Frame(self.root)
        frame.pack(pady = 5)

        tk.Label(frame, text = "From").pack(side = tk.LEFT)
        DateEntry(frame, textvariable = self.start_date, date_pattern = "dd/mm/yyyy", mindate = self.min_date.date(), maxdate = self.max_date.date(), day = self.get_start_date().day, month = self.get_start_date().month, year = self.get_start_date().year).pack(side = tk.LEFT, padx = 5)

        tk.Label(frame, text = "To").pack(side = tk.LEFT)
        DateEntry(frame, textvariable = self.end_date, date_pattern = "dd/mm/yyyy", mindate = self.min_date.date(), maxdate = self.max_date.date(), day = self.get_end_date().day, month = self.get_end_date().month, year = self.get_end_date().year).pack(side = tk.LEFT, padx = 5)

        # Button to refresh chart
        tk.Button(frame, text = "Update chart", command = self.update_chart).pack(side = tk.LEFT, padx = 5)

        # Player filter selection
        frame = tk.Frame(self.root)
        frame.pack(pady = 5)

        tk.Label(frame, text="Filter by").pack(side=tk.LEFT)
        ttk.Combobox(frame, textvariable=self.filter_type, values=[FILTER_TIME_PLAYED, FILTER_DAY_PLAYED]).pack(side=tk.LEFT, padx=5)

        tk.Label(frame, text="Min").pack(side=tk.LEFT)
        tk.Entry(frame, textvariable=self.filter_min, width=5).pack(side=tk.LEFT, padx=5)

        tk.Label(frame, text="Max").pack(side=tk.LEFT)
        tk.Entry(frame, textvariable=self.filter_max, width=5).pack(side=tk.LEFT, padx=5)

        # Player sort selection
        frame = tk.Frame(self.root)
        frame.pack(pady = 5)
        tk.Label(frame, text = "Sort by").pack(side = tk.LEFT)
        tk.Radiobutton(frame, text = "Name", variable = self.sort_mode, value = SORT_NAME, command = self.update_chart).pack(side = tk.LEFT)
        tk.Radiobutton(frame, text = "First seen", variable = self.sort_mode, value = SORT_PLAY_FIRST, command = self.update_chart).pack(side = tk.LEFT)
        tk.Radiobutton(frame, text = "Last seen", variable = self.sort_mode, value = SORT_PLAY_LAST, command = self.update_chart).pack(side = tk.LEFT)
        tk.Radiobutton(frame, text = "Play time", variable = self.sort_mode, value = SORT_PLAY_TIME, command = self.update_chart).pack(side = tk.LEFT)
        tk.Radiobutton(frame, text = "Day played", variable = self.sort_mode, value = SORT_PLAY_DAY, command = self.update_chart).pack(side = tk.LEFT)
        tk.Checkbutton(frame, text = "Reverse sort", variable = self.sort_reverse, command = self.update_chart).pack(side = tk.LEFT)

        # Player representation selection
        frame = tk.Frame(self.root)
        frame.pack(pady = 5)
        tk.Radiobutton(frame, text = "Player name", variable = self.display_mode, value = DISPLAY_NAME, command = self.update_chart).pack(side = tk.LEFT)
        tk.Radiobutton(frame, text = "Player head", variable = self.display_mode, value = DISPLAY_HEAD, command = self.update_chart).pack(side = tk.LEFT)
        tk.Radiobutton(frame, text = "Both", variable = self.display_mode, value = DISPLAY_NAME_AND_HEAD, command = self.update_chart).pack(side = tk.LEFT)

        # Chart type selection
        frame = tk.Frame(self.root)
        frame.pack(pady = 5)
        chart_options = [GRAPH_GANTT_PLAY_TIME, GRAPH_GANTT_PLAY_DAY, GRAPH_LINE_PLAYER_HOUR, GRAPH_LINE_PLAYER_DAY, GRAPH_STACK_BAR_PLAY_TIME, GRAPH_BAR_PLAY_TIME, GRAPH_PIE_PLAY_TIME, GRAPH_PIE_PLAY_DAY]
        chart_menu = ttk.Combobox(frame, textvariable = self.chart_type, values = chart_options)
        chart_menu.pack(side = tk.LEFT, padx = 10)
        chart_menu.bind("<<ComboboxSelected>>", lambda event: self.update_chart())

        # Button to open details
        tk.Button(frame, text = "Show details", command = lambda: self.show_data_list(self.get_filtered_data())).pack(side = tk.LEFT)

    def get_start_date(self):
        return format_datetime(self.start_date.get(), time.min, self.min_date)

    def get_end_date(self):
        return format_datetime(self.end_date.get(), time.max, self.max_date)

    def get_data_dates(self):
        return self.get_start_date(), self.get_end_date()

    def get_filter_min(self):
        return format_number(self.filter_min.get(), 0)

    def get_filter_max(self):
        return format_number(self.filter_max.get(), 0)

    def get_data_filters(self):
        return self.get_filter_min(), self.get_filter_max()

    def get_filtered_data(self):
        start_date, end_date = self.get_data_dates()
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
        # Filter data
        filter_min, filter_max = self.get_data_filters()
        if filter_min > 0 or filter_max > 0:
            if self.filter_type.get() == FILTER_TIME_PLAYED:
                filtered_data = {player: info for player, info in filtered_data.items() if (filter_min <= 0 or info["totalPlayed"] >= (filter_min * 60)) and (filter_max <= 0 or info["totalPlayed"] <= (filter_max * 60))}
            elif self.filter_type.get() == FILTER_DAY_PLAYED:
                filtered_data = {player: info for player, info in filtered_data.items() if (filter_min <= 0 or len(info["dayPlayed"]) >= filter_min) and (filter_max <= 0 or len(info["dayPlayed"]) <= filter_max)}
        # Sort data
        if self.sort_mode.get() == SORT_NAME:
            filtered_data = {player: info for player, info in sorted(filtered_data.items(), key = lambda item: item[0].upper(), reverse = self.sort_reverse.get())}
        elif self.sort_mode.get() == SORT_PLAY_FIRST:
            filtered_data = {player: info for player, info in sorted([item for item in filtered_data.items() if item[1]["sessions"]], key = lambda item: (item[1]["sessions"][0]["start"]), reverse = self.sort_reverse.get())}
        elif self.sort_mode.get() == SORT_PLAY_LAST:
            filtered_data = {player: info for player, info in sorted([item for item in filtered_data.items() if item[1]["sessions"]], key = lambda item: (item[1]["sessions"][-1]["end"]), reverse = self.sort_reverse.get())}
        elif self.sort_mode.get() == SORT_PLAY_TIME:
            filtered_data = {player: info for player, info in sorted(filtered_data.items(), key = lambda item: item[1]["totalPlayed"], reverse = self.sort_reverse.get())}
        elif self.sort_mode.get() == SORT_PLAY_DAY:
            filtered_data = {player: info for player, info in sorted(filtered_data.items(), key = lambda item: len(item[1]["dayPlayed"]), reverse = self.sort_reverse.get())}
        return filtered_data

    def update_chart(self):
        fig = Figure(figsize=(18, 8))
        ax = fig.add_subplot(111)
        filtered_data = self.get_filtered_data()

        # Chart selection logic
        chart_type = self.chart_type.get()
        if chart_type == GRAPH_BAR_PLAY_TIME:
            self.plot_total_time_bar_chart(ax, filtered_data)
        elif chart_type == GRAPH_LINE_PLAYER_DAY:
            self.plot_daily_active_players_line_chart(ax, filtered_data)
        elif chart_type == GRAPH_LINE_PLAYER_HOUR:
            self.plot_hourly_active_players_line_chart(ax, filtered_data)
        elif chart_type == GRAPH_GANTT_PLAY_TIME:
            self.plot_gantt_chart_time(ax, filtered_data)
        elif chart_type == GRAPH_GANTT_PLAY_DAY:
            self.plot_gantt_chart_day(ax, filtered_data)
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

    def plot_hourly_active_players_line_chart(self, ax, data):
        hourly_activity = pd.DataFrame(index=pd.date_range(self.min_date.replace(microsecond=0, second=0, minute=0), self.max_date.replace(microsecond=0, second=0, minute=0), freq='h'))
        hourly_activity['active_players'] = 0
        hourly_active_players = {hour: set() for hour in hourly_activity.index}

        for player, details in data.items():
            for session in details["sessions"]:
                session_start = session["start"]
                session_end = session["end"]
                # Clip session times to fall within the min/max date range
                session_start = max(session_start, self.min_date).replace(microsecond=0, second=0, minute=0)
                session_end = min(session_end, self.max_date).replace(microsecond=0, second=0, minute=0)
                # Create an hourly range for this session
                hourly_range = pd.date_range(session_start, session_end, freq='h')
                # Add the player to the active players set for these hours
                for hour in hourly_range:
                    if hour in hourly_active_players:
                        hourly_active_players[hour].add(player)

        # Convert the sets into counts of unique players
        for hour, players in hourly_active_players.items():
            hourly_activity.loc[hour, 'active_players'] = len(players)

        # Remove empty values at the beginning and end
        first_valid = hourly_activity[hourly_activity['active_players'] > 0].first_valid_index()
        last_valid = hourly_activity[hourly_activity['active_players'] > 0].last_valid_index()
        if first_valid is not None and last_valid is not None:
            hourly_activity = hourly_activity.loc[first_valid:last_valid]

        ax.plot(hourly_activity.index, hourly_activity['active_players'], color='blue', alpha=0.7)
        ax.fill_between(hourly_activity.index, hourly_activity['active_players'], color='lightblue', alpha=0.5)
        ax.set_title("Hourly active players")
        ax.set_xlabel("Hour")
        ax.set_ylabel("Number of active players")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%y %H:%M"))
        ax.tick_params(axis = 'x', rotation = 45)

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

    def plot_gantt_chart_time(self, ax, data):
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

    def plot_gantt_chart_day(self, ax, data):
        dates = pd.date_range(min([min(info["dayPlayed"]) for info in data.values() if info["dayPlayed"]]), (max([max(info["dayPlayed"]) for info in data.values() if info["dayPlayed"]]) + timedelta(days = 1)))

        for i, (player, info) in enumerate([(player, info) for (player, info) in data.items() if info["dayPlayed"]]):
            if self.display_mode.get() in [DISPLAY_HEAD, DISPLAY_NAME_AND_HEAD]:
                player_image = get_player_image(player)
                if player_image:
                    ax.add_artist(AnnotationBbox(OffsetImage(player_image, zoom = 0.1), (min(dates), i), frameon = False, box_alignment = (1.5, 0.5)))
            for day in info["dayPlayed"]:
                ax.barh(player + (' ' * (8 if self.display_mode.get() == DISPLAY_NAME_AND_HEAD else 0)), 1, left = day, color = info["color"])

        for date in dates:
            ax.axvline(date, color = "gray", linestyle = "-", linewidth = 0.5)

        if self.display_mode.get() == DISPLAY_HEAD:
            for label in ax.get_yticklabels():
                label.set_color(plt.matplotlib.colors.to_rgba("white", 0))

        ax.set_title("Active days")
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
        window = tk.Toplevel(self.root)
        window.title("Player data " + (' - '.join([date.strftime(DATE_FORMAT) for date in self.get_data_dates()])))
        window.geometry("250x500")

        # Add a scrollbar
        canvas = tk.Canvas(window)
        canvas.pack(side = "left", fill = "both", expand = 1)
        scrollbar = tk.Scrollbar(canvas, orient = "vertical", command = canvas.yview)
        scrollbar.pack(side = "right", fill = "y")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion = canvas.bbox("all")))
        frame = tk.Frame(canvas, width = 500, height = 100)
        canvas.create_window((0, 0), window = frame, anchor = "nw")

        for player, info in [(player, info) for (player, info) in data.items() if info["sessions"]]:
            label_frame = tk.Frame(frame)
            label_frame.pack(anchor = "w")

            if self.display_mode.get() in [DISPLAY_HEAD, DISPLAY_NAME_AND_HEAD]:
                player_image = get_player_image(player)
                if player_image:
                    player_image = player_image.resize((25, 25))
                    img = ImageTk.PhotoImage(player_image)
                    image = tk.Label(label_frame, image = img)
                    image.image = img
                    image.pack(side = tk.LEFT, padx = (0, 5))
            if self.display_mode.get() in [DISPLAY_NAME, DISPLAY_NAME_AND_HEAD]:
                tk.Label(label_frame, text = f"{player}", font = ("Arial", 12, "bold")).pack(side = tk.LEFT)

            average_session = sum([session["duration"] for session in info["sessions"]]) / len(info["sessions"])
            details = (
                f"First Seen: {info["sessions"][0]['start']}\n"
                f"Last Seen: {info["sessions"][-1]['end']}\n"
                f"Total Played: {floor(info['totalPlayed'] / 60):.0f}H{info['totalPlayed'] % 60:02.0f}\n"
                f"Days Played: {len(info['dayPlayed'])}\n"
                f"Sessions: {len(info["sessions"])}\n"
                f"Average session: {floor(average_session / 60):.0f}H{average_session % 60:02.0f}"
            )
            details_label = tk.Label(frame, text=details, justify="left", font=("Arial", 9))
            details_label.pack(anchor="w", padx=20)

# Run the app
if __name__ == "__main__":
    data, min_date, max_date = parse_data()
    root = tk.Tk()
    app = MinecraftStatsApp(root, data, min_date, max_date)
    root.mainloop()
