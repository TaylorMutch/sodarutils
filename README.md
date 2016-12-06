## Synopsis
A collection of utilities for working with SODAR data.

## Code Example
```python
from sodarutils.collections import SodarCollection, SODAR_FIELDS

# builds the collection
sdrs = SodarCollection('data\McRae')

# available fields accessible
SODAR_FIELDS
{"speed": 0,"direction": 1}

# returns a list of 2D 'speed' data and a dictionary describing the metadata.
data, metadata = sdrs.night_array('speed')

# A 2D array, where each row is a column of wind speeds starting at 15 meters with 10 meter increments. 
data[0]
```

## Motivation
We needed a simple interface for working the the disparate data sources provided to us, as well as a way to group the data into different bins, such as 'nights' or 'days' of data.

## Installation
`pip install git+https://github.com/TaylorMutch/sodarutils.git`

## Contributors

@TaylorMutch

@PeterDrake

Jenny Orr

