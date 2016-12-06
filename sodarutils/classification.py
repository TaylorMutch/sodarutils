
'''
    Collect each of Jerilyn's nights into a dictionary structure, and packs and reloads it from a db if necessary for speed.
    Each element of the list contains a dictionary
'''

import os
import sys
import csv
import sqlite3
import datetime
from sodar_utils import SodarCollection, register_adapters, datetime_to_name

register_adapters()  # registers numpy array adapters


def read_classification_data(path):
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        data = [row for row in reader]

    # Convert 1's and 0's to python booleans
    for row in data:
        for attribute in row.keys():
            if attribute not in ['year','month','day']:
                value = row[attribute]
                row[attribute] = bool(value)

    return data


def _build_from_db(path):

    con = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    with con:
        cur = con.cursor()
        cur.execute("SELECT * FROM night")
        data = cur.fetchall()

    result = [{
        'speeds': row[2],
        'directions': row[3],
        'date': row[1]
    } for row in data]

    return result


def _build_from_sodars(path, night_dates):

    sodars = SodarCollection(path)
    speeds, s_meta = sodars.night_array('speed')
    dirs, d_meta = sodars.night_array('direction')
    result = list()

    for night_date in night_dates:
        try:
            s_index = [i for i, j in enumerate(s_meta) if j['name'] == datetime_to_name(night_date['date'])][0]
            d_index = [i for i, j in enumerate(d_meta) if j['name'] == datetime_to_name(night_date['date'])][0]

            s_data = speeds[s_index]
            d_data = dirs[d_index]

            result.append({
                'speeds': s_data,
                'directions': d_data,
                'date': night_date
            })

        except:
            continue    # bail and move on

    # build a db so we don't have to index every time
    db_path = ''.join([path, os.sep, 'collection.db'])
    if not os.path.exists(db_path):
        con = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        with con:
            cur = con.cursor()
            cur.execute("CREATE TABLE night (id integer primary key, timestamp date, speeds array, directions array)")
            for row in result:
                speed = row['speeds']
                dir = row['directions']
                date = row['date']
                cur.execute("INSERT INTO night VALUES (NULL, ?,?,?)", (date, speed, dir))

    return result


def build_night_classification(directory, class_path):
    """ Generate a list of dictionaries that contain the classification and data for each pair of nights
    :param directory: The directory to the sodar date you want to load.
    :param class_path: The path to the classification data.
    :return: A list of dictionaries containing the classification and raw data for each night.
    """

    # sanity checking
    directory_contents = os.listdir(directory)
    mcrae_path = os.path.abspath(os.path.join(directory, 'McRae'))
    primet_path = os.path.abspath(os.path.join(directory, 'Primet'))
    found_mcrae = 'McRae' in directory_contents and os.path.isdir(mcrae_path)
    found_primet = 'Primet' in directory_contents and os.path.isdir(primet_path)

    if found_mcrae and found_primet:

        classification_db = os.path.abspath(os.path.join(directory, 'classification.db'))
        classification = list()

        if os.path.exists(classification_db):
            con = sqlite3.connect(classification_db, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
            with con:
                cur = con.cursor()
                cur.execute("SELECT * FROM night")
                data = cur.fetchall()

            for row in data:
                classification.append({
                        'date': row[1],
                        'primet_speeds': row[2],
                        'primet_directions': row[3],
                        'mcrae_speeds': row[4],
                        'mcrae_directions': row[5],
                        'meta': {
                            'date': row[1],
                            'mesoscale_forcing': bool(row[6]),
                            'direction': bool(row[7]),
                            'valley_jet': bool(row[8]),
                            'pulsing': bool(row[9]),
                            'similar': bool(row[10]),
                            'year': row[1].year,
                            'month': row[1].month,
                            'day': row[1].day
                        }                   
                    })
                
            return classification

        # else, generate classification, build db, and return
        meta = read_classification_data(class_path)  # the original classification
        night_dates = [row.update({'date': datetime.date(int(row['year']), int(row['month']), int(row['day']))}) for row in meta]

        paths = [mcrae_path, primet_path]
        night_lists = list()

        for path in paths:
            db_path = ''.join([path, os.sep, 'collection.db'])
            if os.path.exists(db_path):
                night_lists.append(_build_from_db(db_path))
            else:
                night_lists.append(_build_from_sodars(path, night_dates))

        mcrae, primet = night_lists

        for m in mcrae:
            for p in primet:
                if m['date'] == p['date']:
                    classification.append({
                        'date': m['date'],
                        'primet_speeds': p['speeds'],
                        'primet_directions': p['directions'],
                        'mcrae_speeds': m['speeds'],
                        'mcrae_directions': p['directions'],
                        'meta': [row for row in meta if row['date'] == m['date']][0]
                    })
                    break

        # build a db so we don't have to index every time
        if not os.path.exists(classification_db):
            con = sqlite3.connect(classification_db, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
            with con:
                cur = con.cursor()
                cur.execute("CREATE TABLE night (id integer primary key, timestamp date,"
                    "primet_speeds array, primet_directions array,"
                    "mcrae_speeds array, mcrae_directions array,"
                    "mesoscale_forcing bool, direction bool, valley_jet bool, pulsing bool, similar bool)")

                for row in classification:
                    t = row['date']
                    ps = row['primet_speeds']
                    pd = row['primet_directions']
                    ms = row['mcrae_speeds']
                    md = row['mcrae_directions']
                    m = row['meta']['mesoscale_forcing']
                    d = row['meta']['direction']
                    v = row['meta']['valley_jet']
                    pu = row['meta']['pulsing']
                    s = row['meta']['similar']
                    cur.execute("INSERT INTO night VALUES (NULL,?,?,?,?,?,?,?,?,?,?)", (t,ps,pd,ms,md,m,d,v,pu,s))

        return classification

    else:
        raise FileNotFoundError('Could not find the McRae and Primet directories. Are you pointing this '
                                'to the right directory?')

if __name__ == '__main__':
    jerilyn_classification = build_night_classification(sys.argv[1], sys.argv[2])
