import matplotlib.pyplot as plt
import numpy as np
import tkinter as tk
import csv
from dateutil.relativedelta import relativedelta
from datetime import datetime

# Constants
DATA_FILE = './data/data.csv'
GRAPH_STACKED_BAR = "Stacked bar chart"
GRAPH_LINE = "Line Chart"
GRAPH_BAR = "Bar chart"
GRAPH_PIE = "Pie Chart"
DEFAULT_TYPE = None
AVAILABLE_GRAPH_TYPE = [GRAPH_STACKED_BAR, GRAPH_LINE, GRAPH_BAR, GRAPH_PIE]

def read_csv():
    with open(DATA_FILE, 'r', encoding='utf-8') as file:
        reader = csv.reader(file, delimiter=';')
        # Read header information
        title, y_label, x_label = next(reader)
        start_month = next(reader)[0]
        # Read data
        categories = []
        colors = []
        values = []
        for row in reader:
            categories.append(row[0])
            colors.append(row[1])
            values.append([int(v) for v in row[2:]])
        # Ensure all lists have the same length
        max_length = max(len(v) for v in values)  # Find the longest list
        for i in range(len(values)):
            values[i] += [0] * (max_length - len(values[i]))
        return title, y_label, x_label, start_month, categories, colors, values

def generate_months(start_month, num_months):
    start_date = datetime.strptime(start_month, "%m-%Y")
    return [(start_date + relativedelta(months=i)).strftime("%b %Y") for i in range(num_months)]

def select_from_list(options, title = "Select an option"):
    result = None  # Variable to store the selected option
    def on_select(value):
        nonlocal result
        result = value
        root.destroy()
    # Create popup window
    root = tk.Tk()
    root.title(title)
    root.geometry("300x" + str(len(options) * 37))
    # Create buttons for each option
    for option in options:
        btn = tk.Button(root, text=option, command=lambda opt=option: on_select(opt))
        btn.pack(pady=5, padx=10, fill="x")
    # Run the event loop
    root.mainloop()
    return result

def plot_stacked_bar_chart(ax, months, categories, colors, values):
    x = np.arange(len(months))
    bottom = np.zeros(len(months))
    for category, color, value in zip(categories, colors, values):
        ax.bar(x, value, label=category, color=color, bottom=bottom)
        bottom += np.array(value)
    ax.set_xticks(x)
    ax.set_xticklabels(months)

def plot_line_chart(ax, months, values):
    total_values = [0] * len(months)
    for value in values:
        for i, val in enumerate(value):
            total_values[i] += val
    ax.plot(months, total_values, color="blue", alpha=0.7)
    ax.fill_between(months, total_values, color="lightblue", alpha=0.5)
    ax.scatter(months, total_values, color="blue", s=50)

def plot_bar_chart(ax, categories, colors, values):
    total_values = [sum(value) for value in values]
    ax.bar(categories, total_values, color=colors)

def plot_pie_chart(ax, categories, colors, values):
    total_values = [sum(value) for value in values]
    ax.pie(total_values, labels=categories, autopct=(lambda val: str(round(val / 100 * sum(total_values)))), startangle=0, colors=colors)


def show_chart(chart_type, show_select = True):
    if chart_type in AVAILABLE_GRAPH_TYPE:
        title, y_label, x_label, start_month, categories, colors, values = read_csv()
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.canvas.manager.set_window_title(title)
        ax.set_title(title)
        ax.set_ylabel(y_label)
        ax.set_xlabel(x_label)
        ax.yaxis.get_major_locator().set_params(integer=True)
        if chart_type == GRAPH_STACKED_BAR:
            plot_stacked_bar_chart(ax, generate_months(start_month, len(values[0])), categories, colors, values)
            ax.legend()
        elif chart_type == GRAPH_LINE:
            plot_line_chart(ax, generate_months(start_month, len(values[0])), values)
        elif chart_type == GRAPH_BAR:
            plot_bar_chart(ax, categories, colors, values)
        elif chart_type == GRAPH_PIE:
            plot_pie_chart(ax, categories, colors, values)
            ax.get_xaxis().set_visible(False)
            ax.get_yaxis().set_visible(False)
        plt.tight_layout()
        plt.show()
    elif show_select:
        return show_chart(select_from_list(AVAILABLE_GRAPH_TYPE, "Select a chart type"), False)

show_chart(DEFAULT_TYPE)
