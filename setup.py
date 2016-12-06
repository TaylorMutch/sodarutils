import os
from setuptools import setup

setup(
    name = "sodarutils",
    version = "0.0.1",
    author = "Taylor Mutch",
    author_email = "taylormutch@gmail.com",
    description = ("A collection of utilities for working with SODAR data."),
    keywords = "sodar",
    url = "https://github.com/TaylorMutch/sodarutils.git",
    packages=['numpy', 'matplotlib'],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities"
    ],
)