## Synopsis
A collection of utilities for working with SODAR data.

## Code Example
```python
from sodarutils.collections import SodarCollection, SODAR_FIELDS
sdrs = SodarCollection('data\McRae')   # builds the collection
SODAR_FIELDS    # available fields accessible
{"speed": 0,"direction": 1}
data, metadata = sdrs.night_array('speed')   # returns a list of 2D 'speed' data and a dictionary describing the metadata.
```

## Motivation
We needed a simple interface for working the the disparate data sources provided to us, as well as a way to group the data into different bins, such as 'nights' or 'days' of data.

## Installation
`pip install git+https://github.com/TaylorMutch/sodarutils.git`

## Contributors
@TaylorMutch
@PeterDrake
Jenny Orr

