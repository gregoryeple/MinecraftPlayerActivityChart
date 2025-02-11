import matplotlib.pyplot as plt
import numpy as np
import csv
from datetime import datetime, timedelta

DATA_FILE = './data/data.csv'

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
    return [(start_date + timedelta(days=30 * i)).strftime("%b %Y") for i in range(num_months)]

def plot_stacked_bar_chart():
    title, y_label, x_label, start_month, categories, colors, values = read_csv()

    num_months = len(values[0])
    months = generate_months(start_month, num_months)

    x = np.arange(len(months))

    fig, ax = plt.subplots(figsize=(10, 6))

    bottom = np.zeros(len(months))

    for category, color, value in zip(categories, colors, values):
        ax.bar(x, value, label=category, color=color, bottom=bottom)
        bottom += np.array(value)

    ax.set_xticks(x)
    ax.set_xticklabels(months, rotation=45, ha='right')
    ax.set_ylabel(y_label)
    ax.set_xlabel(x_label)
    ax.set_title(title)
    ax.legend()

    plt.tight_layout()
    plt.show()


plot_stacked_bar_chart()