#!/usr/bin/python
#
# Script to copy Mac Calendar DB data to clipboard
#   as either schedule data, or busy/avail
# Kevin Marchand - 2016
#

import sqlite3
import datetime
import calendar
import pytz
import getpass
from time import sleep
import subprocess

# copy to clipboard for mac (ref: http://stackoverflow.com/a/25802742)

def write_to_clipboard(output):
    process = subprocess.Popen(
        'pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
    process.communicate(output.encode('utf-8'))

# Setup


local_user = getpass.getuser()

# default timezone
default_timezone = 'America/Toronto'

# days after current date to include
lookahead_day_count = 7

# hour of start of work days (24h clock, in local time)
work_start_hour = 9

# hour of start of work days (24h clock, in local time)
work_end_hour = 17

# show all calendars or only specified ones (see next setting)
show_all_cal = True

# string of calendar IDs in parens (only applies if show_all_cal is False)
# calendar IDs can be identified by running "calendar-avail-listcals.py"
cal_list = '(60)'


# Figure out if timezone offset should be positive or negative from UTC

if datetime.datetime.utcnow() > datetime.datetime.now():
    tz_offset_seconds = abs(datetime.datetime.now() - datetime.datetime.utcnow()).seconds
    tz_offset_seconds = 0 - tz_offset_seconds
else:
    tz_offset_seconds = abs(datetime.datetime.now() - datetime.datetime.utcnow()).seconds


# Offset the start and end times for the db query from the calendar epoch and convert to seconds

epoch_anchor_utc = datetime.datetime.strptime("01-01-2001", "%m-%d-%Y")
query_start_utc = datetime.datetime.utcnow()
query_end_utc = query_start_utc + datetime.timedelta(
    seconds=lookahead_day_count * 24 * 60 * 60)

query_start_seconds = abs((query_start_utc - epoch_anchor_utc).days) * 24 * 60 * 60
query_end_seconds = abs((query_end_utc - epoch_anchor_utc).days) * 24 * 60 * 60

# Connect to Calendar sqlite DB and query events

conn = sqlite3.connect("/Users/%s/Library/Calendars/Calendar Cache" % local_user)
cursor = conn.cursor()

if show_all_cal is True:
    cursor.execute('''select
    	ZSTARTDATE,
    	ZENDDATE,
    	ZTIMEZONE,
    	ZTITLE
        from ZCALENDARITEM
        where ZSTARTDATE > %s
        and ZENDDATE < %s''' % (query_start_seconds, query_end_seconds))
else:
    cursor.execute('''select
    	ZSTARTDATE,
    	ZENDDATE,
    	ZTIMEZONE,
    	ZTITLE
        from ZCALENDARITEM
        where ZSTARTDATE > %s
        and ZENDDATE < %s
        and ZCALENDAR in %s''' % (query_start_seconds, query_end_seconds, cal_list))

calendar_entries = cursor.fetchall()

conn.close()

# convert times from db into datetime objects and sort by start times

calendar_entries_processed = []

for entry in calendar_entries:

    zstartdate = entry[0]
    zenddate = entry[1]
    entry_tz = entry[2]
    title = entry[3]

    try:
        local_tz = pytz.timezone (entry_tz)
    except:
        local_tz = pytz.timezone (default_timezone)

    utc_start = epoch_anchor_utc + datetime.timedelta(seconds=zstartdate)
    utc_start = utc_start.replace(second=0, microsecond=0).replace(tzinfo=pytz.utc)
    utc_end = epoch_anchor_utc + datetime.timedelta(seconds=zenddate)
    utc_end = utc_end.replace(second=0, microsecond=0).replace(tzinfo=pytz.utc)

    calendar_entries_processed.append((utc_start, utc_end, title, entry_tz))

calendar_entries_sorted = sorted(calendar_entries_processed, key=lambda x: x[0])

# Remove all-day events (anything over 23 hours)

for entry in calendar_entries_sorted:
    event_start = entry[0]
    event_end = entry[1]
    if event_end - event_start > datetime.timedelta(hours=23):
        calendar_entries_sorted.remove(entry)

# Build list of the days within the lookahead period, set initial date to today

lookahead_days = []
lookahead_date_utc = datetime.datetime.today().replace(
    hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=pytz.utc)

for x in range(0,lookahead_day_count + 1):
    lookahead_days.append(lookahead_date_utc)
    lookahead_date_utc = lookahead_date_utc + datetime.timedelta(days=1)

# For every date in the lookahead, store all events in the sched_text string

sched_text = ''

for d in lookahead_days:

    wd = calendar.day_name[d.weekday()]
    if wd == 'Saturday' or wd == 'Sunday':
        continue

    sched_text += '\n'
    sched_text += wd + ' - ' + str(d)[:10] + '\n\n'
    entry_count = 0
    for entry in calendar_entries_sorted:
        if entry[0] > d and entry[1] < d + datetime.timedelta(days=1):
            entry_count += 1
            start_local = entry[0].astimezone(pytz.timezone (entry[3]))
            end_local = entry[1].astimezone(pytz.timezone (entry[3]))
            sched_text += str(start_local)[11:16] + ' - ' + \
                str(end_local)[11:16] + ' - ' + entry[2] + '\n'
    if entry_count == 0:
        sched_text += '(No Events)' + '\n'

#  Work out busy/free times and store summary in the basummary_text string

basummary_text = ''

for d in lookahead_days:

    busy_minutes = set()
    day_minutes = set()
    busy_avail = []
    utc = pytz.timezone('UTC')

    # Skip weekends

    wd = calendar.day_name[d.weekday()]
    if wd == 'Saturday' or wd == 'Sunday':
        continue

    # Check if each entry in the overall list of events occured on this date

    for entry in calendar_entries_sorted:

        entry_start = entry[0]
        entry_end = entry[1]

        if entry_start > d and entry_end < d + datetime.timedelta(days=1):

            # Found an event that occurs today

            entry_num_minutes = abs((entry_end - entry_start).seconds) / 60

            # add start minute for the event to the busy_minutes set
            busy_minutes.add(entry_start)

            # add all other minutes that fall within event to the busy_minutes set
            for x in range(1, entry_num_minutes):
                busy_minutes.add(entry_start + datetime.timedelta(minutes=x))

    day_start_local = d.astimezone(pytz.timezone (default_timezone)).replace(
        hour=work_start_hour, minute=0, second=0, microsecond=0)  + datetime.timedelta(hours=24)
    day_end_local = d.astimezone(pytz.timezone (default_timezone)).replace(
        hour=work_end_hour, minute=0, second=0, microsecond=0)  + datetime.timedelta(hours=24)

    day_start = day_start_local.astimezone(utc)
    day_end = day_end_local.astimezone(utc)

    day_num_minutes = abs((day_end - day_start).seconds) / 60

    day_minutes.add(day_start)

    for x in range (1, day_num_minutes):
        m = day_start + datetime.timedelta(minutes=x)
        m_utc = m.astimezone(utc)
        day_minutes.add(m_utc)

    busy_minutes_filtered = set()

    for m in busy_minutes:
        if m < day_end:
            busy_minutes_filtered.add(m)

    avail_minutes = day_minutes.symmetric_difference(busy_minutes_filtered)

    for x in avail_minutes:
        busy_avail.append((x, 'Available'))

    for x in busy_minutes_filtered:
        busy_avail.append((x, 'Busy'))

    busy_avail_sorted = sorted(busy_avail, key=lambda x: x[0])

    # Busy/Avail summary

    basummary_text += '\n'
    basummary_text += wd + ' - ' + str(d)[:10] + '\n\n'

    first_minute = busy_avail_sorted[0][0]
    first_status = busy_avail_sorted[0][1]

    start_of_streak_time = first_minute
    temp_end_time = first_minute + datetime.timedelta(seconds=60)
    temp_last_status = first_status


    for entry in busy_avail_sorted[1:]:
        entry_time = entry[0]
        entry_status = entry[1]

        if entry != busy_avail_sorted[-1]:

            if entry_status == temp_last_status:
                # streak ongoing
                temp_end_time = entry_time + datetime.timedelta(seconds=60)
            else:
                # streak broken
                basummary_text += str(start_of_streak_time.astimezone(
                    pytz.timezone (default_timezone)))[11:16] + ' to ' + str(
                        temp_end_time.astimezone(pytz.timezone (
                                default_timezone)))[11:16] + ' - ' + temp_last_status
                basummary_text += '\n'
                temp_last_status = entry_status
                start_of_streak_time = entry_time

        # last item in list
        else:
            temp_end_time = temp_end_time + datetime.timedelta(seconds=60)
            basummary_text += str(
                start_of_streak_time.astimezone(pytz.timezone (
                    default_timezone)))[11:16] + ' to ' + str(
                        temp_end_time.astimezone(pytz.timezone (
                            default_timezone)))[11:16] + ' - ' + temp_last_status
            basummary_text += '\n'

# comment out one of the two lines below depending on whether the schedule
# summary or busy/available summary shoudl be copied to the clipboard

write_to_clipboard(basummary_text)
# write_to_clipboard(sched_text)
