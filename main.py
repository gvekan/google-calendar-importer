from __future__ import print_function
import datetime
import dateutil.parser
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

importId = '' #Replace with your calendar
insertId = '' #Replace with your calendar
KEYS_TO_KEEP = ['start', 'end', 'summary', 'description', 'location'] #https://developers.google.com/calendar/v3/reference/events/insert
fname = 'update.txt'

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def insert():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)

    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(calendarId=importId, timeMin=now, singleEvents=True,
                                          maxResults=2500, orderBy='updated').execute()
    events = events_result.get('items', [])

    if not events:
        print('No upcoming events found.')

    last_updated = ''

    with open(fname, 'r') as f:
        last_updated = f.read()

    last_updated_dt = dateutil.parser.parse(last_updated)

    for event in events:
        updated = event.get('updated', event.get('created', last_updated))
        updated_dt = dateutil.parser.parse(updated)
        if updated_dt > last_updated_dt:
            new = {}
            for key in KEYS_TO_KEEP:
                value = event.get(key, None)
                if value is not None:
                    new[key] = value
            e = service.events().insert(calendarId=insertId, body=new).execute()
            print('Event created: %s' % (e.get('htmlLink')))
        else:
            print('No more to update')
            break


    with open(fname, 'w') as f:
        f.write(now)

def remove(): #Use to clean insert calendar
    """Shows basic usage of the Google Calendar API.
       Prints the start and name of the next 10 events on the user's calendar.
       """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)

    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    events_result = service.events().list(calendarId=insertId, timeMin=now,
                                          maxResults=2500, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    for event in events:
        id = event.get('id', None)
        if id is not None:
            service.events().delete(calendarId=insertId, eventId=id).execute()


if __name__ == '__main__':
    insert()