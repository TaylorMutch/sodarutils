"""
    Taylor Mutch,
    Revision date - 11/23/2016

    Utilities for working with the VALCEX data.
    timestamp in this context will refer to either a Sodar timestamp (e.x. 120314124500),
    or a datetime.datetime object (e.x. datetime(2012, 3, 14, 12, 45))
"""
import os
import sys
import numpy as np
import datetime
import sqlite3
import io

months = [None, "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# tags for direction, speed, SDR (timestamp) and height in .sdr file
TAGS = {'DCL', 'VCL', 'SDR', 'H  '}

SODAR_FIELDS = {
    "speed": 0,
    "direction": 1
}


def plural_names(bands):
    """ Allow for plural names to be used """

    result = dict()
    result.update(bands)
    other_names = {band+'s':bands[band] for band in bands.keys()}
    result.update(other_names)
    return result


# Meta information for the data structure
MAX_TIMESTAMPS = 288                                # 288 5-minute periods in 1 day
NO_DATA = -1
NIGHT_START_INDEX = 18*60//5                        # start at 1800
NIGHT_STOP_INDEX = NIGHT_START_INDEX + 12*60//5 + 1 # stop at 0600 the next day, +1 gives us 0600 included in the night reading
NIGHT_SIZE = NIGHT_STOP_INDEX - NIGHT_START_INDEX   # 144 timestamps


def read_sdr(filepath):
    """
    Base file reader. Returns raw Sodar data
    @return Heights, timestamps, speeds and directions each as 1D or 2D arrays
    """

    with open(os.path.abspath(filepath)) as datafile:
        data = datafile.readlines()

    timestamps = list()
    speeds = list()
    directions = list()
    heights = list()

    for line in data:
        tag = line[:3]
        if tag in TAGS:
            if tag == 'H  ' and len(heights) == 0:
                heights = [int(j) for j in line.strip().split()[1:]]
            elif tag == 'VCL':
                speeds.append([float(j) for j in line.strip().split()[1:]])
            elif tag == 'DCL':
                directions.append([float(j) for j in line.strip().split()[1:]])
            elif tag == 'SDR':
                timestamps.append(int(line[4:16]))

    # Check that everything is as it should be
    assert(len(speeds) == len(directions) == len(timestamps))

    return heights, timestamps, speeds, directions


def timestamp_to_datetime(timestamp):
    """ Convert Sodar timestamp to datetime.datetime object """
    t = str(timestamp)
    year = int(t[:2])
    month = int(t[2:4])
    day = int(t[4:6])
    hour = int(t[6:8])
    minute = int(t[8:10])
    return datetime.datetime(year,month,day,hour,minute)


def name_to_datetime(name):
    """ Generates a datetime.datetime object based on Sodar file name/date """

    year = 2000 # years aren't important in names, unless there are cross year data (i.e. midnight on Dec. 31)
    if (os.path.isfile(name)):
        date = filepath.split(os.sep).split('.')[0]
        return datetime.datetime(year, int(date[0:2]), int(data[2:4]))
    else:
        return datetime.datetime(year, int(name[0:2]), int(name[2:4]))


def datetime_to_name(timestamp):
    """ Reproduces a MMDD name for Sodar files from datetime.datetime object """

    mm = timestamp.month
    if mm < 10:
        mm = '0{mm}'.format(mm=mm)
    else:
        mm = str(mm)

    dd = timestamp.day
    if dd < 10:
        dd = '0{dd}'.format(dd=dd)
    else:
        dd = str(dd)

    return mm + dd


class _FakeSource(object):
    """ A stand-in/filler class for representing missing data.
        Name implies that this class is interior to the class,
        and should therefore not be used outside of the class
    """

    def __init__(self, name, heights, timestamps):
        self.name = str(name)
        self.heights = heights
        self.data = np.empty((len(SODAR_FIELDS.keys()), MAX_TIMESTAMPS, len(self.heights)))
        self.data.fill(NO_DATA)
        self.timestamps = timestamps[:]
        # adjust timestamps month and days to match the name
        for i in range(len(self.timestamps)):
            adjusted_timestamp = str(self.timestamps[i])
            adjusted_timestamp = adjusted_timestamp[0:2] + self.name + adjusted_timestamp[6:len(adjusted_timestamp)] 
            self.timestamps[i] = int(adjusted_timestamp)



class SodarCollection(object):
    """
        A collection of Sodar records from a directory of data sources.

        # ************* Accessing each timestamp ************** #
        each entry in a band is a timestamp
        each timestamp has values, starting from height 0 to height max_height

        Timestamp values are stored in self.timestamps (raw values in self._timestamps),
        and the index of the timestamp is used as the accessor into the larger dataset

        I.e. values at index 0 are at height[0], and values at index[33] are at height[33]
        --> data[band][timestamp_idx][value]

        E.x. Accessing a row of data
        
        Import everything
        >>> from sodar_utils import *
        build collection
        >>> sodars = SodarCollection('path/to/sodar/station')  
        Get timestamp 
        >>> timestamp = timestamp_to_datetime(120312125500)
        >>> timestamp_idx = sodars.timestamps.index(timestamp)
        ... or equivalently
        >>> timestamp = 120312125500
        >>> timestamp_idx = sodars._timestamps.index(timestamp)
        Now access the data
        >>> row_data = sodars.dataset[0][timestamp_idx]
        >>> print(row_data)
        # or as a normal python list
        >>> print(row_data.tolist())
    """


    def __init__(self, directory, make_db=False):

        # build independent data sources
        self.name = directory.split(os.sep)[-1]
        #self.sources = list()
        sources = list()
        for root, dirs, files in os.walk(directory):    # since our naming convention is mmdd, order of the files guarantees the order we have valid timestamp orders
            for path in files:        
                if path.split('.')[-1] in ['sdr', 'SDR']:
                    sources.append(Sodar(os.path.join(root, path)))

        assert(len(sources) > 0)    # don't create collection if no sources were found

        self.sources = list()
        self._base_timestamp = sources[0].name
        current_day = name_to_datetime(self._base_timestamp)
        self.sources.append(sources[0])

        if len(sources) > 0:

            for i in range(1, len(sources)):
                next_day = name_to_datetime(sources[i].name)
                delta = next_day - current_day
                # Test if we need to insert sources for missing dates between actual sources
                if delta.days > 1:
                    # dates missing, add fake sources up until next_day
                    fake_source_date = current_day + datetime.timedelta(days=1)
                    while fake_source_date < next_day:
                        fake_name = datetime_to_name(fake_source_date)
                        self.sources.append(_FakeSource(fake_name,
                                                             sources[0].heights,
                                                             sources[0].timestamps))
                        fake_source_date += datetime.timedelta(days=1)
                self.sources.append(sources[i])
                current_day = name_to_datetime(sources[i].name)

        # now connect the data sources
        self.dataset = None
        self._timestamps = list()   # _timestamps are the raw timestamps
        self.heights = list()
        for source in self.sources:
            if self.dataset is None:
                self.dataset = source.data
                self.heights = source.heights   # collect heights once, should be uniform accross all sources
            else:
                a = self.dataset
                b = source.data
                self.dataset = np.concatenate((a,b), axis=1)   # we want to join along the time axis
            self._timestamps += source.timestamps

        self._day_index = [i*MAX_TIMESTAMPS for i in range(len(self.sources))]
        self._night_index = [
            {
                'name': self.sources[i].name,
                'start': self._day_index[i] + NIGHT_START_INDEX,
                'stop': self._day_index[i] + NIGHT_STOP_INDEX
            } for i in range(len(self.sources) - 1)]    # -1 since we don't have data for the morning after the last timestamp

        # Generate datetime.datetime objects for all the timestamps
        self.timestamps = [timestamp_to_datetime(timestamp) for timestamp in self._timestamps]


        # Assert that there exists exactly 5 minutes between each record across all sources,
        # and that they are in the proper order
        for i in range(1, len(self.timestamps)):
            a = self.timestamps[i-1]
            b = self.timestamps[i] - datetime.timedelta(minutes=5)
            assert(a == b)

        if make_db:
            generate_db(os.path.join(directory, 'sodar_collection.db'))


    def source_dates(self, use_all=False):
        """ Return the dates for all the valid sources. Excludes non-data sources if use_all = False"""
        return [source.name for source in self.sources if type(source) == Sodar or use_all]


    def night_array(self, band, partial=False, use_all=False, select_nights=None):
        """ Returns a 2-Tuple of a list of 2D arrays for all nights for the given band, and the accessor data associated with it as a dictionary
            @param partial Flag whether to include nights where either the evening or morning readings are missing.
            @param use_all Flag whether to include all nights, regardless of any other settings.
            @param nights A list of nights to return. Ignores flags if parameter is a list and has valid night dates/names.
        """

        # List that will contain our dictionaries
        night_index = list()

        # Logic for responding to parameters
        if select_nights is not None and type(select_nights) is list:   # Select only those nights asked for
            for night in self._night_index:
                for selected_night in select_nights:
                    if night['name'] == selected_night:
                        night_index.append(night)
                        break
        elif use_all:                       # Get everything
            night_index = self._night_index
        else:
            for i in range(1, len(self.sources)):   # Choose every source where evening and morning are valid (partial) sources
                if (type(self.sources[i-1]) == Sodar and type(self.sources[i]) == Sodar):
                    night_index.append(self._night_index[i-1])
                elif (partial and (type(self.sources[i-1]) is Sodar or type(self.sources[i]) is Sodar)):
                    night_index.append(self._night_index[i-1])

        if (len(night_index) == 0):
            raise ValueError("No nights were available. True using 'partial' or 'use_all' set to 'True' to see if values exist at all.")

        # Slice out the night data we want
        band_idx = plural_names(SODAR_FIELDS)[band]
        num_nights = len(night_index)
        result = None
        band_data = self.dataset[band_idx]
        for night in night_index:
            night_data = band_data[night['start']:night['stop']]
            if result is None:
                result = night_data
            else:
                result = np.concatenate((result, night_data), axis=0)

        # reshape to size of night and return array and night_index
        return (result.reshape(num_nights, NIGHT_SIZE, len(self.heights)),night_index)


def adapt_array(arr):
    """
    http://stackoverflow.com/a/31312102/190597 (SoulNibbler)
    Adapts a numpy array to fit into a single column entry.
    """
    out = io.BytesIO()
    np.save(out, arr)
    out.seek(0)
    return sqlite3.Binary(out.read())

def convert_array(text):
    """ Loads a numpy array from a bytes object """
    out = io.BytesIO(text)
    out.seek(0)
    return np.load(out)


def register_adapters():
    # Converts np.array to TEXT when inserting
    sqlite3.register_adapter(np.ndarray, adapt_array)

    # Converts TEXT to np.array when selecting
    sqlite3.register_converter("array", convert_array)

register_adapters()


def generate_db(sodars, path):
    """ Generate an sqlite3 database from a collection """

    con = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)

    with con:
        cur = con.cursor()

        # we want to store the speeds, directions, datetime for the night
        #cur.execute("CREATE TABLE s_collection (id integer primary key, name text)") # TODO - add a table for multiple collections

        cur.execute("CREATE TABLE s_array (id integer primary key, night date, speeds array, directions array)")
        speeds, _ = sodars.night_array('speeds')
        dirs, meta = sodars.night_array('directions')

        i = 0
        for night in meta:
            start = night['start']
            stop = night['stop']
            night_date = sodars.timestamps[start].date()    # builtin's are for date and time, not datetime. We only need the date anyway
            night_speeds = speeds[i]
            night_dirs = dirs[i]
            cur.execute("INSERT INTO s_array VALUES (?,?,?)", (night_date, night_speeds, night_dirs))
            i += 1

    # test the db
    with con:
        try:
            cur = con.cursor()
            cur.execute("SELECT * from s_array")
            cur.fetchone()
        except sqlite3.Error:
            print("An error occurred in fetching data from the db. Db is non-functional.")

def timestamp_to_index(timestamp):
    """ Converts Sodar timestamps to dataset indices for a single Sodar source """
    
    time_str = str(timestamp)
    return (int(time_str[6:8]) * 60 + int(time_str[8:10])) // 5


class Sodar(object):
    """
        A collection of Sodar records from a single source.

        # ********************** NOTE *************************** #
        -1 is used as the fill value for the datasets.
        This accounts for having an uneven number of height points 
        across different weather conditions / events that cause 
        no-data gaps to occur

    """

    def __init__(self, fp):

        self._extract_bands(fp)

    def _extract_bands(self, filepath):
        """ 
            Pack SDR data into numpy arrays.
        Builds a numpy array with two bands that holds velocity and direction
        """
        self.name = filepath.split(os.sep)[-1].split('.')[0]
        self.heights, self.timestamps, speeds, directions = read_sdr(filepath)
        self.data = np.empty((len(SODAR_FIELDS.keys()), MAX_TIMESTAMPS, len(self.heights)))
        self.data.fill(NO_DATA)                                        # 0 is speeds, 1 is directions
        for j in range(len(speeds)):
            time_idx = timestamp_to_index(self.timestamps[j])
            for i in range(len(speeds[j])):
                self.data[0][time_idx][i] = speeds[j][i]
                self.data[1][time_idx][i] = directions[j][i]

        # At this point we can discard and regenerate the timestamps since
        # some can be missing, but now they are filled with NO_DATA for every 5 minute interval
        if len(self.timestamps) != MAX_TIMESTAMPS:
            # Reassign them based on file name and year
            base_timestamp = str(self.timestamps[0])[:6]
            date = base_timestamp[:6]
            self.timestamps = list()
            seconds = '00'  # seconds are always 0
            for i in range(MAX_TIMESTAMPS):
                hours, minutes = divmod(i*5, 60)
                if hours < 10:
                    hours = '0' + str(hours)
                else:
                    hours = str(hours)
                if minutes < 10:
                    minutes = '0' + str(minutes)
                else:
                    minutes = str(minutes)
                self.timestamps.append(int(base_timestamp + hours + minutes + '00'))   # seconds 


if __name__ == "__main__":

    # Get the raw date
    heights, dates, speeds, directions = read_sdr(sys.argv[1])

    # Create a collection of sodar data
    sodars = SodarCollection(sys.argv[1])

