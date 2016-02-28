#!/usr/bin/python
#
# Script to list calendar IDs from Mac Calendar DB
# Kevin Marchand - 2016
#

import sqlite3
import getpass

local_user = getpass.getuser()

conn = sqlite3.connect("/Users/%s/Library/Calendars/Calendar Cache" % local_user)
cursor = conn.cursor()
cursor.execute('''select
    Z_PK,
    ZTITLE
    from znode
    where ZTITLE not null''')
calendar_list = cursor.fetchall()
conn.close()

print '\n'
print 'ID\tCALENDAR NAME'

for cal in calendar_list:
    print str(cal[0]) + '\t' + cal[1]

print '\n\n'
