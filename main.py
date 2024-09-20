from datetime import datetime as dt, timedelta
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
import seaborn as sns

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

def plot_wait_time():
    print("Plotting wait time")

    wait_time_data = pd.read_csv('PIT_security_wait_time.csv')
    wait_time_data.columns = ['checkpoint', 'minutes', 'time']

    wait_time_data['time'] = pd.to_datetime(wait_time_data['time']).dt.tz_localize('utc')
    wait_time_data['local_time'] = wait_time_data['time'].dt.tz_convert('US/Eastern')

    # col_wrap = 1, height = 2 and aspect=2
    g = sns.FacetGrid(wait_time_data, col='checkpoint', col_wrap=4, height=4, aspect=1.5)

    # Map the lineplot to each subplot
    g.map(sns.lineplot, 'local_time', 'minutes', marker='o', markersize=4)

    # Customize the x-axis for each plot to show day of week and time, with ticks every 3 hours
    for ax in g.axes.flatten():
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%a %H:%M'))
        ax.xaxis.set_major_locator(plt.matplotlib.dates.HourLocator(interval=3))
        ax.tick_params(axis='x', rotation=45)  # Rotate x-axis labels for readability

    # Add a common title and adjust layout
    # g.figure.suptitle('Line Plot by Category with Date and Time on X-Axis', y=0)
    g.set_axis_labels('Day of Week and Time')

    # Adjust layout to avoid overlapping
    plt.tight_layout()
    # plt.show()

    g.savefig("wait_time_at_pit.png") 

if __name__ == "__main__":
    ## Record production_load_time
    production_load_time = dt.now()
    print(production_load_time)

    get_wait_time_at_pit()

    plot_wait_time()