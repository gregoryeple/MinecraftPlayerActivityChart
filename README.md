# Minecraft Player Activity Charts

A simple Python program made to visualize the data collected by the ComputerCraft program [SpyBot.lua](https://github.com/gregoryeple/ComputerCraftPrograms/blob/main/spybot.lua) by putting them in different types of charts.

> The collected data must be placed inside the data directory in order the be visualized.

# Log Extractor

A secondary program made to extract data from a minecraft server logs and create a new file usable by the main program.

> The logs must be in the .gz format and they must be placed inside the data directory.

# Examples

![Daily active players example chart](https://github.com/gregoryeple/MinecraftPlayerActivityChart/blob/master/examples/daily-active-players.png?raw=true)
![Play sessions example chart](https://github.com/gregoryeple/MinecraftPlayerActivityChart/blob/master/examples/play-sessions.png?raw=true)

[See more examples](https://github.com/gregoryeple/MinecraftPlayerActivityChart/tree/master/examples)

# Custom Monthly Chart
A simple python program originally designed to display custom data from a .csv file in a monthly stacked bar chart.

Can now be used to display the data with different type of charts (Stacked bar / Line / Bar / Pie), but only the stacked bar chart will display all of the provided data as the other types will either loose the categories or the dates.

The .csv file used by default is `./data/data.csv` and its content must follow the following format:
- 1st line: `Chart title;Y axis title;X axis title`
- 2nd line: `Starting month (MM-YYYY format)`
- Other lines `Category name;Category color (#RRGGBB);Category values per month`
