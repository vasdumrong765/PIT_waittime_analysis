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

def get_wait_time_at_PIT():
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

def get_flights_schedule_at_PIT():
    print("Getting flights schedule")
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


if __name__ == "__main__":
    ## Record production_load_time
    production_load_time = dt.now()
    print(production_load_time)

    get_wait_time_at_PIT()

    # only run the next script if the time is +/- 5min from the exact hour
    # current_minutes = production_load_time.minute
    # if (current_minutes <= 10) or (current_minutes >= 50):
    #     get_flights_schedule_at_PIT()