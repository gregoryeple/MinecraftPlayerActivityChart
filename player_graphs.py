import os
import re
from datetime import datetime
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

        # Filter data by date range
        filtered_data = {
            player: {
                "sessions": [session for session in info["sessions"] if session["start"].date() >= start_date and session["end"].date() <= end_date],
                "totalPlayed": info["totalPlayed"],
                "dayPlayed": [day for day in info["dayPlayed"] if start_date <= day <= end_date]
            }
            for player, info in self.data.items()
        }

        # Chart selection logic
        chart_type = self.chart_type.get()

        if chart_type == "bar":
            self.plot_total_time_bar_chart(ax, filtered_data)
        elif chart_type == "line":
            self.plot_daily_active_players_line_chart(ax, filtered_data)
        elif chart_type == "gantt":
            self.plot_gantt_chart(ax, filtered_data)
        elif chart_type == "stacked_bar":
            self.plot_daily_play_time_stacked_bar_chart(ax, filtered_data)
        elif chart_type == "pie_total":
            self.plot_total_time_pie_chart(ax, filtered_data)
        elif chart_type == "pie_days":
            self.plot_active_days_pie_chart(ax, filtered_data)
        elif chart_type == "list":
            self.show_data_list(filtered_data)
            return  # No plot needed for list

        # Display figure in tkinter
        for widget in self.root.winfo_children():
            if isinstance(widget, FigureCanvasTkAgg):
                widget.get_tk_widget().destroy()

        # Display figure in tkinter
        canvas = FigureCanvasTkAgg(fig, self.root)
        canvas.get_tk_widget().pack()
        canvas.draw()

    # Chart plotting methods
    def plot_total_time_bar_chart(self, ax, data):
        players = list(data.keys())
        total_played_hours = [info["totalPlayed"] / 60 for info in data.values()]  # Convert minutes to hours

        ax.bar(players, total_played_hours, color="skyblue")
        ax.set_title("Total Time Played by Each Player")
        ax.set_xlabel("Players")
        ax.set_ylabel("Total Time Played (hours)")
        ax.tick_params(axis='x', rotation=45)

    def plot_daily_active_players_line_chart(self, ax, data):
        all_dates = pd.date_range(self.min_date, self.max_date)
        daily_active_counts = {date: 0 for date in all_dates}

        for info in data.values():
            for day in info["dayPlayed"]:
                if day in daily_active_counts:
                    daily_active_counts[day] += 1

        dates = list(daily_active_counts.keys())
        active_counts = list(daily_active_counts.values())

        ax.plot(dates, active_counts, color="blue", alpha=0.7)
        ax.fill_between(dates, active_counts, color="lightblue", alpha=0.5)
        ax.set_title("Daily Active Players")
        ax.set_xlabel("Date")
        ax.set_ylabel("Number of Active Players")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m-%Y"))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator())
        ax.tick_params(axis='x', rotation=45)

    def plot_gantt_chart(self, ax, data):
        players = list(data.keys())
        y_pos = range(len(players))

        for i, (player, info) in enumerate(data.items()):
            for session in info["sessions"]:
                ax.barh(player, (session["end"] - session["start"]).total_seconds() / (60 * 60 * 24),
                        left=session["start"], color="green", edgecolor="black")

        ax.set_title("Player Sessions (Gantt Chart)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Players")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m-%Y"))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator())
        ax.tick_params(axis='x', rotation=45)

    def plot_daily_play_time_stacked_bar_chart(self, ax, data):
        all_dates = pd.date_range(self.min_date, self.max_date)
        daily_play_times = {player: [0] * len(all_dates) for player in data.keys()}

        for i, date in enumerate(all_dates):
            for player, info in data.items():
                daily_play_time = sum(
                    (session["end"] - session["start"]).total_seconds() / 3600
                    for session in info["sessions"] if session["start"].date() == date.date()
                )
                daily_play_times[player][i] += daily_play_time

        dates = list(all_dates)
        bottom = np.zeros(len(dates))
        for player, play_times in daily_play_times.items():
            ax.bar(dates, play_times, bottom=bottom, label=player)
            bottom += np.array(play_times)

        ax.set_title("Daily Play Time (Stacked Bar Chart)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Total Play Time (hours)")
        ax.legend()
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m-%Y"))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator())
        ax.tick_params(axis='x', rotation=45)

    def plot_total_time_pie_chart(self, ax, data):
        players = list(data.keys())
        total_played_hours = [info["totalPlayed"] / 60 for info in data.values()]

        ax.pie(total_played_hours, labels=players, autopct="%1.1f%%", startangle=140, colors=plt.cm.Paired.colors)
        ax.set_title("Total Play Time Distribution")

    def plot_active_days_pie_chart(self, ax, data):
        players = list(data.keys())
        active_days_count = [len(info["dayPlayed"]) for info in data.values()]

        ax.pie(active_days_count, labels=players, autopct="%1.1f%%", startangle=140, colors=plt.cm.Paired.colors)
        ax.set_title("Active Days Distribution")

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
