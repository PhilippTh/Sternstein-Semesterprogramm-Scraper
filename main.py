from __future__ import print_function
import httplib2
import os
import datetime
from datetime import timedelta
import requests
import re
from bs4 import BeautifulSoup
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Sternstein Python Scraper'

def get_credentials():
    """Gets valid user credentials from storage.
    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.
    Returns: Credentials, the obtained credential."""
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'calendar-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def main():
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    event = {
      'summary': item["title"],
      'description': item["notes"],
      'start': {
        'dateTime': item["start_datetime"],
        'timeZone': 'Europe/Vienna',
      },
      'end': {
        'dateTime': item["end_datetime"],
        'timeZone': 'Europe/Vienna',
      },
      'reminders': {
        'useDefault': True,
      },
    }

    event = service.events().insert(calendarId='7rt3vc5jrsqi7sml9v97ljrneg@group.calendar.google.com', body=event).execute()
    print ('Event created: %s' % (event.get('htmlLink')))

response = requests.get("http://www.sternstein.net/semesterprogramm.html")
soup = BeautifulSoup(response.content, "html.parser")
div = soup.find("div", attrs={"class": "content clearfix"})

date, title, values = None, None, []
items = []

def appending (d, v):
    items.append({
                "date": d,
                "endtime": None,
                "values": v
            })

for elem in div.contents:
    if elem.name == "h3" and elem.text != "\xa0":
        if values:
            appending(date, values)
            values = []
        date = elem.text
    elif elem.name == "h3" and elem.text == "\xa0":
        values.append(elem.text)
    elif elem.name == "h2" and elem.text == "\xa0":
        values.append(elem.text)
    elif elem.name == "p":
        values.append(elem.text)
appending(date, values)
values = []

today = datetime.date.today()
if "Dezember" in div.text:
    if today.month in range(8, 12):
        next_year = today.year + 1
        this_year = today.year
    elif today.month in range(1, 7):
        next_year = today.year
        this_year = today.year - 1
else:
    next_year = today.year + 1
    this_year = today.year

def list_splitter(values, delim):
    items = []
    item = []
    for value in values:
        if value == delim:
            if item:
                items.append(item)
            item = []
        else:
            item.append(value)
    return items

processed = []

for item in items:
    for details in list_splitter(item["values"], "\xa0"):
        processed.append({
            "start_datetime": item["date"],
            "end_datetime": None,
            "title": details[0],
            "notes": details[1:]
        })

for item in processed:
    date = item["start_datetime"]
    two_days = re.compile("(\d*)./(\d*).(\d*)")
    more_days = re.compile("(\d*).-(\d*).(\d*)")
    one_day = re.compile("(\d*).(\d*)")
    time = re.compile("(\d*:\d*)")
    d, d_end, m, t, t_end = None, None, None, None, None
    
    if two_days.match(date):
        day = two_days.match(date)
        d = day.group(1)
        d_end =day.group(2)
        m = day.group(3)

    elif more_days.match(date):
        day = more_days.match(date)
        d = day.group(1)
        d_end =day.group(2)
        m = day.group(3)

    elif one_day.match(date):
        day = one_day.match(date)
        d = day.group(1)
        d_end = d
        m = day.group(2)

    for value in item["notes"]:
        if time.match(value) and not t:
            found_time = time.match(value)
            t = found_time.group(1) + ":00"
            control = "23:00:00"
            t_converted = datetime.datetime.strptime(t, '%H:%M:%S')+ datetime.timedelta(hours = 1)
            c_converted = datetime.datetime.strptime(control, '%H:%M:%S')
            if t_converted >= c_converted:
                t_end = "23:59:59"
            else:
                t_end = t_converted.strftime('%H:%M:%S')
        item["notes"]= [" ".join(item["notes"][0:])]
               
    if t:
        if "Dezember" in div.text:
            if m == "9" or m == "10" or m == "11" or m == "12":
                item["start_datetime"] = str(this_year) + "-" + m + "-" + d + "T" + t
                item["end_datetime"] = str(this_year) + "-" + m + "-" + d_end + "T" + t_end
            else:
                item["start_datetime"] = str(next_year) + "-" + m + "-" + d + "T" + t
                item["end_datetime"] = str(next_year) + "-" + m + "-" + d_end + "T" + t_end
        else:
            item["start_datetime"] = str(this_year) + "-" + m + "-" + d + "T" + t
            item["end_datetime"] = str(this_year) + "-" + m + "-" + d_end + "T" + t_end
    else:
        d_end = int(d_end) + 1
        if "Dezember" in div.text:
            if m == "9" or m == "10" or m == "11" or m == "12":
                item["start_datetime"] = str(this_year) + "-" + m + "-" + d + "T" + "00:00:00"
                item["end_datetime"] = str(this_year) + "-" + m + "-" + str(d_end) + "T" + "00:00:00"
            else:
                item["start_datetime"] = str(next_year) + "-" + m + "-" + d + "T" + "00:00:00"
                item["end_datetime"] = str(next_year) + "-" + m + "-" + str(d_end) + "T" + "00:00:00"
        else:
            item["start_datetime"] = str(this_year) + "-" + m + "-" + d + "T" + "00:00:00"
            item["end_datetime"] = str(this_year) + "-" + m + "-" + str(d_end) + "T" + "00:00:00"        

for item in processed:
    print(item)
main()
