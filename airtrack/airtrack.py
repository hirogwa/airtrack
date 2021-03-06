from datetime import datetime, timedelta
import click
import re
import subprocess
import sqlite3

from airtrack import settings

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
                 ' VALUES (NULL, ?, ?)'),
    'count_by_ssid': ('select count(1) from airport_checkin' +
                      '  where timestamp between ? and ?' +
                      '  and ssid = ?'),
    'count_by_timestamp': ('select count(1) from airport_checkin' +
                           '  where timestamp = ?')
}

HELP = {
    'datapoint_size': 'Weight of a data point in minutes.',
    'ssid': ('SSID to filter the data points by.'
             + ' Defaults to the current network if not given.')
}

DB_PATH = None

TIME_FORMAT_MIN = '%Y-%m-%d %H:%M'
TIME_FORMAT_SEC = '%Y-%m-%d %H:%M:%S'
time_string_minute = lambda x: x.strftime(TIME_FORMAT_MIN)
time_string_second = lambda x: x.strftime(TIME_FORMAT_SEC)


@click.group()
@click.option('--debug/--no-debug', default=False)
def cli(debug):
    global DB_PATH
    if debug:
        click.echo('Running airtrack with debug mode')
        DB_PATH = settings.DB_PATH_DEBUG
    else:
        DB_PATH = settings.DB_PATH
    click.echo('Using database at {}'.format(DB_PATH))


@cli.command()
def init_db():
    '''
    Initializes the database at the first use.
    '''
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(STATEMENTS['create_table'])
        cur.execute(STATEMENTS['create_index_timestamp'])


@cli.command()
@click.option('-b', '--bulk/--no-bulk', default=False,
              help='Register a range.')
@click.option('-s', '--since')
@click.option('-t', '--till', default=datetime.now().strftime(TIME_FORMAT_MIN))
@click.option('-p', '--datapoint-size', default=1, help=HELP['datapoint_size'])
def register(bulk, since, till, datapoint_size):
    '''
    Registers the current airport connection entry.
    '''
    if bulk:
        if not since:
            click.echo('--since parameter is required in bulk mode', err=True)
            return

    ssid = get_current_ssid()
    if not ssid:
        click.echo("You don't seem to be on any network")
        return

    if bulk:
        delta = timedelta(minutes=datapoint_size)
        from_time = datetime.strptime(since, TIME_FORMAT_MIN)
        to_time = datetime.strptime(till, TIME_FORMAT_MIN)
        with sqlite3.connect(DB_PATH) as conn:
            inserted, skipped = register_airport_range(
                conn, from_time, to_time, delta, ssid)
        m_str = lambda x: '{} {}'.format(x, 'minute' if x == 1 else 'minutes')
        click.echo(
            '{} to {} by {} on network {}: {} registered, {} skipped'
            .format(since, till, m_str(datapoint_size),
                    ssid, inserted, skipped))

    else:
        target_time = datetime.now()
        with sqlite3.connect(DB_PATH) as conn:
            inserted = register_airport(conn, target_time, ssid, True)
        click.echo(
            '{} on network {}: {} registered, {} skipped'
            .format(target_time.strftime(TIME_FORMAT_SEC), ssid,
                    int(inserted), int(not inserted)))


@cli.command()
@click.option('-s', '--since',
              default=datetime.min.strftime(TIME_FORMAT_MIN))
@click.option('-t', '--till',
              default=datetime.now().strftime(TIME_FORMAT_MIN))
@click.option('-p', '--datapoint-size', default=1, help=HELP['datapoint_size'])
@click.option('-i', '--ssid', help=HELP['ssid'])
def total(since, till, datapoint_size, ssid):
    '''
    Shows the cumulative amount of time on the specified network
    for the specified time range.
    '''
    from_time = datetime.strptime(since, TIME_FORMAT_MIN)
    to_time = datetime.strptime(till, TIME_FORMAT_MIN)
    return sum_up(from_time, to_time, datapoint_size, ssid)


@cli.command()
@click.option('-p', '--datapoint-size', default=1, help=HELP['datapoint_size'])
@click.option('-i', '--ssid', help=HELP['ssid'])
def today(datapoint_size, ssid):
    '''
    Shows the cumulative amount of time on the specified network today.
    '''
    to_time = datetime.now()
    from_time = datetime(to_time.year, to_time.month, to_time.day)
    return sum_up(from_time, to_time, datapoint_size, ssid)


@cli.command()
@click.option('-p', '--datapoint-size', default=1, help=HELP['datapoint_size'])
@click.option('-i', '--ssid', help=HELP['ssid'])
def past_day(datapoint_size, ssid):
    '''
    Shows the cumulative amount of time on the specified network
    for the past day.
    '''
    return sum_up_to_now(timedelta(days=1), datapoint_size, ssid)


@cli.command()
@click.option('-p', '--datapoint-size', default=1, help=HELP['datapoint_size'])
@click.option('-i', '--ssid', help=HELP['ssid'])
def past_week(datapoint_size, ssid):
    '''
    Shows the cumulative amount of time on the specified network
    for the past week.
    '''
    return sum_up_to_now(timedelta(weeks=1), datapoint_size, ssid)


@cli.command()
@click.option('-p', '--datapoint-size', default=1, help=HELP['datapoint_size'])
@click.option('-i', '--ssid', help=HELP['ssid'])
def past_month(datapoint_size, ssid):
    '''
    Shows the cumulative amount of time on the specified network
    for the past month.
    '''
    to_time = datetime.now()
    if to_time.month == 1:
        from_time = datetime(to_time.year - 1, 12, to_time.day,
                             to_time.hour, to_time.minute, to_time.second,
                             to_time.microsecond)
    else:
        from_time = datetime(to_time.year, to_time.month - 1, to_time.day,
                             to_time.hour, to_time.minute, to_time.second,
                             to_time.microsecond)
    return sum_up(from_time, to_time, datapoint_size, ssid)


def sum_up_to_now(delta, datapoint_size, ssid):
    to_time = datetime.now()
    from_time = to_time - delta
    return sum_up(from_time, to_time, datapoint_size, ssid)


def sum_up(from_time, to_time, datapoint_size, ssid, output=True):
    if not ssid:
        click.echo('SSID not specified. Setting the current network.')
        ssid = get_current_ssid() or ''

    datapoint_count = 0
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        rs = cur.execute(STATEMENTS['count_by_ssid'], (
            time_string_second(from_time),
            time_string_second(to_time),
            ssid))
        row = rs.fetchone()
        datapoint_count = row[0]

    h, m = divmod(datapoint_count * datapoint_size, 60)
    if output:
        click.echo(
            'Cumulative time on %s from %s to %s is %02dh:%02dm'
            % (ssid,
               time_string_minute(from_time),
               time_string_minute(to_time),
               h, m))
    return h, m


def register_airport(conn, timestamp, ssid, skip_dupl=False):
    cur = conn.cursor()
    time_str = time_string_second(timestamp)
    if skip_dupl:
        rs = cur.execute(STATEMENTS['count_by_timestamp'], (time_str,))
        row = rs.fetchone()
        if row[0] > 0:
            return False

    cur.execute(STATEMENTS['register'], (time_str, ssid))
    return True


def register_airport_range(conn, from_time, to_time, delta, ssid):
    insert_count, skip_count = 0, 0
    target_time = from_time
    while target_time < to_time:
        if register_airport(conn, target_time, ssid, skip_dupl=True):
            insert_count += 1
        else:
            skip_count += 1
        target_time += delta
    return insert_count, skip_count


def get_current_ssid():
    cmd_out = subprocess.run(
        [AIR_COMMAND, '-I'], stdout=subprocess.PIPE).stdout
    ssid_entry = re.search('\sSSID:.*\n', cmd_out.decode('utf-8'))
    if ssid_entry:
        return ssid_entry.group().split('SSID: ')[1].rstrip('\n')
    else:
        return None
