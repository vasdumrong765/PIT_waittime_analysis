from datetime import datetime as dt
import numpy as np
import pandas as pd
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
import chromedriver_autoinstaller
chromedriver_autoinstaller.install()
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.collections import LineCollection
import seaborn as sns
import pytz

pd.set_option('display.max_colwidth', None)
sns.set_context("talk", font_scale=1)

def get_wait_time_at_pit():
    print("Getting Security Wait time")
    # PGH airport website uses javascript elements that load after html
    # Need to combine selenium webpage interaction with bs4 to get the correct information
    options = ChromeOptions()
    options.add_argument("--headless")
    browser = webdriver.Chrome(options=options)
    browser.get("https://flypittsburgh.com/pittsburgh-international-airport/terminal-information/safety-security/")
    delay = 10 # seconds

    wait = WebDriverWait(browser, delay)

    element_1 = wait.until(EC.presence_of_element_located((By.ID, "tsalabel")))
    element_2 = wait.until(EC.presence_of_element_located((By.ID, "mainwaitlabel")))

    # Function to wait until both elements' text is not empty (non-null)
    def wait_until_both_elements_have_text(element1, element2, timeout=10):
        try:
            # Wait for both elements to have non-null text using a custom condition
            WebDriverWait(browser, timeout).until(
                lambda browser: element1.text.strip() != '' and element2.text.strip() != ''
            )
            # print(f"Both elements have non-empty text!\nElement 1: {element1.text.strip()}\nElement 2: {element2.text.strip()}")
        except TimeoutException:
            print("One or both elements' text did not become non-null within the given timeout period.")

    # Wait until both elements' text is non-null (not empty)
    wait_until_both_elements_have_text(element_1, element_2)

    html_source = browser.page_source
    browser.quit()

    soup = BeautifulSoup(html_source,'html.parser')  

    out = pd.DataFrame({
            'Location':['TSA_Pre', 'Main', 'First_Class', 'Alt_Checkpoint'],
            'Wait_time_minutes':[
                soup.find('strong', {'id': 'tsalabel'}).text.strip(),
                soup.find('strong', {'id': 'mainwaitlabel'}).text.strip(),
                soup.find('strong', {'id': 'firstclasslabel'}).text.strip(),
                soup.find('strong', {'id': 'altwaitlabel'}).text.strip()]
        })
    out['Wait_time_minutes'] = pd.to_numeric(out['Wait_time_minutes'].str.replace('Min', ''), errors='coerce')
    out['production_load_dt']=production_load_time
    out.to_csv("PIT_security_wait_time.csv", mode='a', index=False, header=False)
    print("successfully ran the script - Get TSA wait time")

# Function to get color for day of the week
def get_day_color(date):
    day_of_week = date.strftime('%a')
    colors = {
        'Mon': 'yellow',
        'Tue': 'pink',
        'Wed': 'green',
        'Thu': 'orange',
        'Fri': 'blue',
        'Sat': 'purple',
        'Sun': 'red'
    }
    return colors.get(day_of_week, 'black')  # Default to black if not matched

# Function to plot each line with different colors for 0 and non-0 values
def plot_with_segmented_colors(ax, x, y):
    points = np.array([mdates.date2num(x), y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    # Define the colors based on whether the values are zero
    colors = ['#ff7f0e' if y_val == 0 else '#1f77b4' for y_val in y]

    # Create a LineCollection, passing the segments and colors
    lc = LineCollection(segments, colors=colors, linewidth=2)
    
    # Add the LineCollection to the plot
    ax.add_collection(lc)
    ax.autoscale()

def plot_wait_time():
    print("Plotting wait time")

    wait_time_data = pd.read_csv('PIT_security_wait_time.csv')
    wait_time_data.columns = ['checkpoint', 'minutes', 'time']

    # Define US/Eastern timezone
    us_eastern = pytz.timezone('US/Eastern')

    wait_time_data['time'] = pd.to_datetime(wait_time_data['time']).dt.tz_localize('utc')
    wait_time_data['local_time'] = wait_time_data['time'].dt.tz_convert(us_eastern)
    wait_time_data = wait_time_data.sort_values(by='local_time')

    wait_time_data['minutes'].fillna(0, inplace=True)
    # print(wait_time_data.head())

    # col_wrap = 1, height = 2 and aspect=2
    g = sns.FacetGrid(wait_time_data, col='checkpoint', col_wrap=2, height=4, aspect=1.5)

    # Map the lineplot to each subplot
    for ax, checkpoint in zip(g.axes.flat,wait_time_data['checkpoint'].unique()):
        subset = wait_time_data[wait_time_data['checkpoint'] == checkpoint]
        
        # Plot the line with color based on value (gray for 0, blue for non-zero)
        plot_with_segmented_colors(ax, subset['local_time'], subset['minutes'])

        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%m-%d %a %H:%M', tz=us_eastern))
        ax.xaxis.set_major_locator(plt.matplotlib.dates.HourLocator(interval=3))
        ax.tick_params(axis='x', rotation=90)  # Rotate x-axis labels for readability

        # Get the tick labels
        tick_labels = ax.get_xticklabels()
        # Update the tick label colors based on the day of the week
        for label in tick_labels:
            date = mdates.num2date(label.get_position(), tz=us_eastern)[0]  # Convert tick position to datetime
            label.set_color(get_day_color(date))  # Set the color based on the day

    # Add a common title and adjust layout
    g.set_axis_labels('Day of Week and Time')

    # Adjust layout to avoid overlapping
    plt.tight_layout()
    # plt.show()

    g.savefig("wait_time_at_pit.png") 


def plot_wait_time_average():
    ## Import wait time data
    # Make sure to use one directory up for data with ../
    wait_time_data = pd.read_csv('PIT_security_wait_time.csv')
    wait_time_data.columns = ['checkpoint', 'minutes', 'time']

    # Define US/Eastern timezone
    us_eastern = pytz.timezone('US/Eastern')
    wait_time_data['time'] = pd.to_datetime(wait_time_data['time']).dt.tz_localize('utc')
    wait_time_data['local_time'] = wait_time_data['time'].dt.tz_convert(us_eastern)
    wait_time_data = wait_time_data.sort_values(by='local_time')

    # Impute missing values as 0
    wait_time_data.fillna({'minute':0}, inplace=True)

    # Extract hour and day of week from the timestamp
    wait_time_data["hour"] = wait_time_data["local_time"].dt.hour
    wait_time_data["day_of_week"] = wait_time_data["local_time"].dt.day_name()
    wait_time_data["day_order"] = wait_time_data["local_time"].dt.dayofweek  # Monday=0, Sunday=6

    # Create a single timeline from Monday midnight to Sunday 11pm
    wait_time_data["timeline"] = wait_time_data["day_order"] * 24 + wait_time_data["hour"]

    # Group data by timeline and day of week, calculate mean and standard deviation
    agg_wait_time_data = wait_time_data.groupby(["checkpoint","timeline", "day_of_week"]).agg(
        mean_wait_time=("minutes", "mean"),
        std_wait_time=("minutes", "std")
    ).reset_index()

    # print(agg_wait_time_data.head())

    # Define colors for each day of the week
    day_colors = {
        "Monday": "#FFB3BA",
        "Tuesday": "#FFDFBA",
        "Wednesday": "#FFFFBA",
        "Thursday": "#BAFFC9",
        "Friday": "#BAE1FF",
        "Saturday": "#D5BAFF",
        "Sunday": "#FFC4BA",
    }

    # Set Seaborn style
    sns.set_theme(style="dark", context="notebook")

    # Customize grid to make it sparser
    plt.rcParams["grid.color"] = "white"
    plt.rcParams["grid.linestyle"] = "--"
    plt.rcParams["grid.linewidth"] = 1
    plt.rcParams["axes.facecolor"] = "#0d1117"
    plt.rcParams["axes.edgecolor"] = "#444444"
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["xtick.color"] = "black"
    plt.rcParams["ytick.color"] = "black"
    plt.rcParams["axes.labelcolor"] = "black"
    plt.rcParams["axes.titlecolor"] = "black"

    g = sns.FacetGrid(wait_time_data, col='checkpoint', col_wrap=2, height=4, aspect=1.5)

    # Map the lineplot to each subplot
    for ax, checkpoint in zip(g.axes.flat, agg_wait_time_data['checkpoint'].unique()):
        subset = agg_wait_time_data[agg_wait_time_data['checkpoint'] == checkpoint]
            
        for day in subset["day_of_week"].unique():
            day_data = subset[subset["day_of_week"] == day]
            color = day_colors.get(day, "black")
            ax.plot(day_data["timeline"], day_data["mean_wait_time"], label=day, color=color)
            ax.fill_between(
                day_data["timeline"],
                day_data["mean_wait_time"] - day_data["std_wait_time"],
                day_data["mean_wait_time"] + day_data["std_wait_time"],
                color=color,
                alpha=0.2)


        # Generate x-axis labels
        xticks = range(0, 168)  # Tick for every hour
        xlabels = [
            f"{['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][i // 24]} {i % 24:02d}:00"
            if i % 3 == 0 else ""
            for i in xticks
        ]
        ax.set_xticks(ticks=xticks, labels=xlabels, fontsize=6)
        ax.tick_params(axis='x', rotation=90, which='both', bottom=True, top=False)  # Rotate x-axis labels for readability
        ax.set_title(checkpoint)

    # Add a common title and adjust layout
    g.set_axis_labels('Day of Week and Time')
    g.figure.suptitle('Average security wait time at PIT airport from Sept to Dec 2024')
    g.set_ylabels("Wait time (minutes)")

    # Adjust layout to avoid overlapping
    plt.tight_layout()
    # plt.show()
    g.savefig("wait_time_at_pit.png") 


if __name__ == "__main__":
    ## Record production_load_time
    production_load_time = dt.now()
    print(production_load_time)

    get_wait_time_at_pit()

    plot_wait_time_average()