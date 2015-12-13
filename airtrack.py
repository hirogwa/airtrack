from datetime import datetime
import re
import subprocess
import sqlite3

DB_PATH = 'airtrack.db'
AIR_COMMAND = ('/System/Library/PrivateFrameworks/Apple80211.framework/'
               + 'Versions/Current/Resources/airport')

STATEMENTS = {
    'create_table': (' CREATE TABLE airport_checkin (' +
                     '   id        INTEGER PRIMARY KEY,' +
                     '   timestamp TEXT,' +
                     '   ssid      TEXT' +
                     ' )'),
    'create_index_timestamp': (' CREATE INDEX airport_checkin_timestamp' +
                               '   on airport_checkin (timestamp)'),
    'register': (' INSERT INTO airport_checkin (id, timestamp, ssid)' +
                 ' VALUES (NULL, ?, ?)')
}


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(STATEMENTS['create_table'])
        cur.execute(STATEMENTS['create_index_timestamp'])


def register_current_airport():
    entry = get_current_airplay()
    if entry:
        with sqlite3.connect(DB_PATH) as conn:
            register(conn, *entry)


def get_current_airplay():
    cmd_out = subprocess.run(
        [AIR_COMMAND, '-I'], stdout=subprocess.PIPE).stdout
    ssid_entry = re.search('\sSSID:.*\n', cmd_out.decode('utf-8'))
    if ssid_entry:
        ssid = ssid_entry.group().split('SSID: ')[1].rstrip('\n')
        return (datetime.now(), ssid)
    else:
        print('No SSID identified')
        return None


def register(conn, timestamp, ssid):
    cur = conn.cursor()
    cur.execute(STATEMENTS['register'], (timestamp, ssid))


def airtrack():
    register_current_airport()
    # init_db()

if __name__ == '__main__':
    airtrack()
