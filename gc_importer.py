from __future__ import print_function
import datetime
import dateutil.parser
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from ics import Calendar
import requests
import collections

KEYS_TO_KEEP = ['end', 'start', 'anyoneCanAddSelf', 'attachments', 'attendees', 'colorId', 'conferenceData',
                'description', 'extendedProperties', 'gadget', 'guestsCanInviteOther', 'guestsCanModify',
                'guestsCanSeeOtherGuests', 'location', 'originalStartTime', 'recurrence', 'reminders', 'sequence',
                'source', 'status', 'summary', 'transparency', 'visibility']

# Keys checked on time-edit, google calendar
ICS_KEYS = ['BEGIN', 'END', 'DSTART', 'DTEND', 'UID', 'DSTAMP', 'LAST-MODIFIED', 'SUMMARY', 'LOCATION', 'DESCRIPTION',
            'CREATED', 'RRULE', 'SEQUENCE', 'STATUS', 'TRANSP', 'X-GOOGLE-HANGOUT']

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.events']


def get_ics(url):
    '''
    print('{}'.format(requests.get(url).text))
    '''
    response = requests.get(url).text.splitlines()
    value = response.pop(0)
    while value != 'BEGIN:VEVENT':
        value = response.pop(0)

    events = []
    event = {}
    key = ''
    skip = False
    for r in response:
        if skip:
            skip = False
            continue

        pair = r.split(':', 1)

        if pair[0] in ICS_KEYS or pair[0][:2] == 'X-':
            key = pair[0]
            if key=='END':
                events.append(event)
                event = {}
                skip = True
                continue
            elif len(pair) > 1:
                value = pair[1]
            else:
                continue # Empty key
        elif len(pair) > 1:
            value = event[key] + pair[0] + ':' + pair[1]
        else:
            value = pair[0] + ':'

        event[key] = value

def get_gc_service():
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
    return build('calendar', 'v3', credentials=creds)


def strip_gc_event(event):
    stripped = {}
    for key in KEYS_TO_KEEP:
        value = event.pop(key, None)
        if value is not None:
            stripped[key] = value
    return stripped


def list_gc(calId, filter, timeMax=None):
    service = get_gc_service()
    events = []
    timeMin = datetime.datetime.utcnow().isoformat() + 'Z'
    if isinstance(timeMax, str):
        if dateutil.parser.parse(timeMin) < dateutil.parser.parse(timeMin):
            events = service.events().list(calendarId=calId, timeMin=timeMin, timeMax=timeMax,
                                           maxResults=2500, orderBy='updated').execute().get('items', [])
    else:
        events = service.events().list(calendarId=calId, timeMin=timeMin,
                                       maxResults=2500, orderBy='updated').execute().get('items', [])

    for f in filter:
        try:
            if len(f)==2:
                remove = []
                for index, e in enumerate(events):
                    value = e.get(f[0], None)
                    try:
                        if f[1] in value:
                            remove.append(index)
                    except:
                        continue
                for i in reversed(remove):
                    events.pop(i)
        except:
            continue

    return events

def split_data(calId, update_file):
    data = ''
    with open(update_file, 'r') as f:
        data = f.read().splitlines(True)

    oldEventsId = {}
    last_updated_dt = None
    index = -1
    for i, d in enumerate(data):
        if d.startswith(calId):
            values = d.split(',')[1:]
            last_updated_dt = dateutil.parser.parse(values.pop(0))
            for v in values:
                pair = v.split('>')
                oldEventsId[pair[0]] = pair[1]
            index = i
            break
    if index>=0:
        data.pop(index)

    return data, last_updated_dt, oldEventsId


def insert(calId, events, update_file):
    service = get_gc_service()

    data, last_updated_dt, oldEventsId = split_data(calId, update_file)

    addedEventsId = {}
    for e in events:
        updated = e.get('updated', e.get('created', None))
        if updated is not None:
            updated_dt = dateutil.parser.parse(updated)
            id = e.get('id', '')
            if last_updated_dt is not None and id in oldEventsId:
                if last_updated_dt >= updated_dt:
                    print('Event up to date')
                    continue
                else:
                    service.events().delete(calendarId=calId, eventId=id).execute()
                    oldEventsId.pop(id)
                    print('Event modified to date')

            e = strip_gc_event(e)
            event = service.events().insert(calendarId=calId, body=e).execute()
            print('Event created: %s' % (event.get('id')))
            addedEventsId[id] = event.get('id')

    oldEventsId.update(addedEventsId)
    with open(update_file, 'w') as f:
        d = [calId, datetime.datetime.utcnow().isoformat() + 'Z']
        for key, value in oldEventsId.items():
            d.append(key + '>' + value)
        data.append(','.join(d))
        f.write('\n'.join(data))


def removeInserts(calId, update_file):
    service = get_gc_service()
    data, last_updated_dt, oldEventsId = split_data(calId, update_file)

    for id in oldEventsId:
        service.events().delete(calendarId=calId, eventId=id).execute()

    with open(update_file, 'w') as f:
        f.write('\n'.join(data))


def clean(calId, update_file):
    service = get_gc_service()

    data, last_updated_dt, oldEventsId = split_data(calId, update_file)

    with open(update_file, 'w') as f:
        f.write('\n'.join(data))

    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    events_result = service.events().list(calendarId=calId, timeMin=now,
                                          maxResults=2500, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    for event in events:
        id = event.get('id', None)
        if id is not None:
            service.events().delete(calendarId=calId, eventId=id).execute()


