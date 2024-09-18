from datetime import datetime as dt
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

## Record production_load_time
production_load_time = dt.now()
print(production_load_time)

## Scrape flight schedule information using selenium Chrome and BeautifulSoup
options = ChromeOptions()
options.add_argument("--headless")
browser = webdriver.Chrome(options=options)
browser.get("https://www.flightstats.com/v2/flight-tracker/departures/PIT")
delay = 10 # seconds

wait = WebDriverWait(browser, delay)

html_source = browser.page_source
browser.quit()

soup = BeautifulSoup(html_source,'html.parser')  

## Search for flights data (in json format)
# store flight data strings
text = '__NEXT_DATA__ ='
search_text = soup.find_all(lambda tag: tag.name == "script" and text in tag.text)
if len(search_text)==1:
    flight_data_str = search_text[0].text.strip()

# Extract the JSON portion from the string
start_index = flight_data_str.find('__NEXT_DATA__ = ') + len('__NEXT_DATA__ = ')
json_data_str = flight_data_str[start_index:]
json_data_str = json_data_str[:json_data_str.find('};')+1]  # Extract the JSON part
flight_data = json.loads(json_data_str)  # Parse the JSON

## Grab flight information from the parsed data
record_lookup_date = flight_data['props']['initialState']['flightTracker']['route']['header']['date']
record_lookup_date = dt.strptime(record_lookup_date, "%d-%b-%Y").strftime("%Y-%m-%d")
print(record_lookup_date)

flights = flight_data['props']['initialState']['flightTracker']['route']['flights']

# Create a list to hold flight details
flight_records = []

# Iterate over each flight in the data
for flight in flights:
    # Extract basic flight details
    flight_number = flight['carrier']['flightNumber']
    departure_airport = "PIT" # Fixed as all flights depart from PIT
    departure_time = flight['departureTime']['time24']
    arrival_airport = flight['airport']['fs']
    arrival_time = flight['arrivalTime']['time24']
    airline_name = flight['carrier']['name']
    airline_code = flight['carrier']['fs']
    
    # Extract codeshare information (if available)
    is_codeshare = flight.get('isCodeshare', False)
    operating_carrier = flight.get('operatedBy', '')
    
    # Add flight details to the records list
    flight_records.append({
        'Flight_Number': flight_number,
        'Departure_Airport': departure_airport,
        'Departure_Time': departure_time,
        'Arrival_Airport': arrival_airport,
        'Arrival_Time': arrival_time,
        'Airline': airline_name,
        'Code': airline_code,
        'Is_Codeshare': is_codeshare,
        'Operating_Carrier': operating_carrier
    })

# Create a pandas DataFrame from the flight records
df = pd.DataFrame(flight_records)
df['production_load_dt']=production_load_time
df_nocodeshare = df[df['Is_Codeshare']==False]

# Display the DataFrame
# print(df.head().T)
# print(df_nocodeshare.head().T)

df_nocodeshare.to_csv("PIT_schedule.csv", mode='a', index=False, header=False)
print("successfully ran the script - Get PIT schedule")