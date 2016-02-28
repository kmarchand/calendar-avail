# calendar-avail
Python script to copy Mac Calendar data to clipboard

Running the script will copy either a schedule summary or a busy/available list to the clipboard.  Which one it copies is set at the end of the script (comment out one or the other):

```python
write_to_clipboard(basummary_text)
# write_to_clipboard(sched_text)
```

`basummary_text` is a summary of times that are either busy or available and `sched_text` is a list of scheduled events.

Settings at the start of the file can be used to specify the look-ahead day count (how many days to include), the start and end of the work day and whether or not to show all calendars or specific calendars.


### Specify Calendars

To specify calendars, modify the settings at the start of the script to change `show_all_cal` to `False` and populate `cal_list` with a list of calendar IDs (in paren, comma separated).  The `calendar-avail-listcals.py` script can be run to get a list of calendar IDs.

### Timezones

Please note, the default timezone is set at the start of the script to `'America/Toronto'`.  It should hopefully work if you are in a different timezone and update that setting to match (using a value from here: http://stackoverflow.com/q/13866926), but I haven't tested for other timezones.
