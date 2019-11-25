"""
bigcty.py - part of classabbyamp/ctyparser
---

Copyright 2019 classabbyamp, 0x5c
Released under the terms of the MIT license.
"""


import json
import tempfile
import zipfile
import pathlib
import re
import os
import collections
from datetime import datetime

import requests
import feedparser

from typing import Union


default_feed = "http://www.country-files.com/category/big-cty/feed/"


class BigCty(collections.abc.Mapping):
    """BigCty
    ------

    Class representing a BigCTY dataset.
    Can be initialised with data by passing the path
    to a valid 'cty.json' file to the constructor.

    Methods:

    `.load()` a 'cty.json' file. Overwrites the internal data.

    `.dump()` the data to a 'cty.json' file.

    `.import_dat()` directly import data from a 'cty.dat' file.

    `.update()` the data from the internet.

    Attributes:

    `.version`: the datestamp of the data, YYYYMMDD format.

    `.formatted_version`: a more human friendly representation of the datestamp.
    """
    regex_version_entry = re.compile(r"VER(\d{8})")
    regex_feed_date = re.compile(r'(\d{2}-\w+-\d{4})')
    regex_dat = re.compile(r"""=?(?P<prefix>[a-zA-Z0-9/]+)
                                 (?:\((?P<cq>\d+)\))?
                                 (?:\[(?P<itu>\d+)\])?
                                 (?P<latlong>
                                     <(?P<lat>[+-]?\d+(?:\.\d+)?)
                                     \/
                                     (?P<long>[+-]?\d+(?:.\d+)?)>
                                 )?
                                 (?:\{(?P<continent>\w+)\})?
                                 (?:~(?P<tz>[+-]?\d+(?:\.\d+)?)~)?""", re.X)

    def __init__(self, file_path: Union[str, os.PathLike, None] = None):
        self._data: dict = {}
        self.version = ""

        if file_path is not None:
            self.load(file_path)

    def load(self, cty_file: Union[str, os.PathLike]) -> None:
        """Loads a cty.json file into the instance.

        Args:
            cty_file (str or os.PathLike): Path to the file to load.
        """
        cty_file = pathlib.Path(cty_file)
        with cty_file.open("r") as file:
            ctyjson = json.load(file)
            self.version = ctyjson.pop("version", None)
            self._data = ctyjson

    def dump(self, cty_file: Union[str, os.PathLike]) -> None:
        """Dumps the data of the instance to a cty.json file.

        Args:
            cty_file (str or os.PathLike): Path to the file to dump to.
        """
        cty_file = pathlib.Path(cty_file)
        datadump = self._data.copy()
        datadump["version"] = self.version
        with cty_file.open("w") as file:
            json.dump(datadump, file)

    def import_dat(self, dat_file: Union[str, os.PathLike]) -> None:
        """Imports CTY data from a cty.dat file.

        Args:
            dat_file (str or os.PathLike): Path to the file to import.
        """
        dat_file = pathlib.Path(dat_file)
        with dat_file.open("r") as file:
            cty_dict = dict()

            ver_match = re.search(self.regex_version_entry, file.read())
            self.version = ver_match.group(1) if ver_match is not None else ""
            file.seek(0)

            last = ''
            while True:
                line = file.readline().rstrip('\x0D').strip(':')
                if not line:
                    break
                if line != '' and line[0].isalpha():
                    segments = [x.strip() for x in line.split(':')]
                    if segments[7][0] == '*':
                        segments[7] = segments[7][1:]
                        segments[0] += ' (not DXCC)'
                    cty_dict[segments[7]] = {'entity': segments[0], 'cq': int(segments[1]),
                                             'itu': int(segments[2]), 'continent': segments[3],
                                             'lat': float(segments[4]), 'long': float(segments[5]),
                                             'tz': -1*float(segments[6]), 'len': len(segments[7])}
                    last = segments[7]

                elif line != '' and line[0].isspace():
                    overrides = line.strip().rstrip(';').rstrip(',').split(',')
                    for item in overrides:
                        if item not in cty_dict.keys():
                            data = cty_dict[last]
                            match = re.search(self.regex_dat, item)
                            if match is None:
                                continue
                            if match.group("itu"):
                                data['itu'] = int(match.group("itu"))
                            if match.group("cq"):
                                data['cq'] = int(match.group("cq"))
                            if match.group("latlong"):
                                data['lat'] = float(match.group("lat"))
                                data['long'] = float(match.group("long"))
                            if match.group("continent"):
                                data['continent'] = match.group("continent")
                            if match.group("tz"):
                                data['tz'] = -1 * float(match.group("tz"))
                            prefix = match.group("prefix")
                            cty_dict[prefix] = data
        self._data = cty_dict

    def update(self) -> bool:
        """Upates the instance's data from the feed.

        Returns:
            True if an update was done, otherwise False.
        """
        with requests.Session() as session:
            feed = session.get(default_feed)
            parsed_feed = feedparser.parse(feed.content)
            update_url = parsed_feed.entries[0]['link']
            date_match = re.search(self.regex_feed_date, update_url)
            if date_match is None:
                raise Exception("Error parsing feed: date missing")  # TODO: Better exception
            date_str = date_match.group(1).title()
            update_date = datetime.strftime(datetime.strptime(date_str, '%d-%B-%Y'), '%Y%m%d')

            if self.version == update_date:
                return False

            with tempfile.TemporaryDirectory() as temp:
                path = pathlib.PurePath(temp)
                dl_url = f'http://www.country-files.com/bigcty/download/bigcty-{update_date}.zip'  # TODO: Issue #10
                rq = session.get(dl_url)
                with open(path / 'cty.zip', 'wb+') as file:
                    file.write(rq.content)
                    zipfile.ZipFile(file).extract('cty.dat', path=str(path))  # Force cast as str because mypy
                self.import_dat(path / "cty.dat")
        return True

    @property
    def formatted_version(self) -> str:
        """Formatted representation of the version/date of the current BigCTY data.
        "0000-00-00" if invalid datestamp."""
        try:
            return datetime.strptime(self.version, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            return "0000-00-00"

    # --- Wrappers to implement dict-like functionality ---
    def __len__(self):
        return len(self._data)

    def __getitem__(self, key: str):
        return self._data[key]

    def __iter__(self):
        return iter(self._data)

    # --- Standard methods we should all implement ---
    # str(): Simply return what it would be for the underlaying dict
    def __str__(self):
        return str(self._data)

    # repr(): Class name, instance ID, and last_updated
    def __repr__(self):
        return (f'<{type(self).__module__}.{type(self).__qualname__} object'
                f'at {hex(id(self))}, last_updated={self.last_updated}>')
