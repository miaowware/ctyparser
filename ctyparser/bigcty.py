"""
bigcty.py - part of miaowware/ctyparser
---

Copyright 2019-2020 classabbyamp, 0x5c
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
    """Class representing a BigCTY dataset.
    Can be initialised with data by passing the path to a valid ``cty.json`` file to the constructor.

    :param file_path: Location of the ``cty.json`` file to load.
    :type file_path: str or os.PathLike, optional

    :var version: the datestamp of the data, ``YYYYMMDD`` format.
    :vartype version: str
    """
    regex_version_entry = re.compile(r"VER(\d{8})")
    regex_feed_date = re.compile(r'(\d{2}-\w+-\d{4})')
    
    # sample data for regex_dat:
    # IB9
    # =II0GDF/9
    # =IT9ACJ/I/BO
    # AA0(4)[7]
    
    # explanation:
    # starting with optional '=' 
    #     (If an alias prefix is preceded by ‘=’, this indicates that the 
    #      prefix is to be treated as a full callsign, i.e. must be an exact match.)
    # Named group 'prefix': one or more of characters (both cases), numbers and '/'
    # Optional non-capturing group, named group 'cq' inside of '()' capturing numbers 
    #     ((#) Override CQ Zone)
    # Optional non-capturing group, named group 'itu' inside of '[]' capturing numbers 
    #     ([#] Override ITU Zone)
    # Optional named group 'latlong', inside of '<>' two named groups 'lat' and 'long' separated by '/'
    #     (<#/#> Override latitude/longitude)
    # Optional non-capturing group, named group 'continent' inside of '{}' capturing characters 
    #     ({aa} Override Continent)
    # Optional non-capturing group, named group 'tz' inside of '~~' 
    #     (~#~ Override local time offset from GMT)
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
        self._version = ""

        if file_path is not None:
            self.load(file_path)

    def load(self, cty_file: Union[str, os.PathLike]) -> None:
        """Loads a ``cty.json`` file into the instance.

        :param cty_file: Path to the file to load.
        :type cty_file: str or os.PathLike
        :return: None
        """
        cty_file = pathlib.Path(cty_file)
        with cty_file.open("r") as file:
            ctyjson = json.load(file)
            self._version = ctyjson.pop("version", None)
            self._data = ctyjson

    def dump(self, cty_file: Union[str, os.PathLike]) -> None:
        """Dumps the data of the instance to a ``cty.json`` file.

        :param cty_file: Path to the file to dump to.
        :type cty_file: str or os.PathLike
        :return: None
        """
        cty_file = pathlib.Path(cty_file)
        datadump = self._data.copy()
        datadump["version"] = self._version
        with cty_file.open("w") as file:
            json.dump(datadump, file)

    def import_dat(self, dat_file: Union[str, os.PathLike]) -> None:
        """Imports CTY data from a ``CTY.DAT`` file.

        :param dat_file: Path to the file to import.
        :type dat_file: str or os.PathLike
        :return: None
        """
        dat_file = pathlib.Path(dat_file)
        with dat_file.open("r") as file:
            cty_dict = dict()

            # get the version from the file, set filepointer to beginning of file afterwards
            ver_match = re.search(self.regex_version_entry, file.read())
            self._version = ver_match.group(1) if ver_match is not None else ""
            file.seek(0)

            # variable to store last DXCC introduction with countryname, zones, etc. for further use
            last = ''
            
            while True:
                # read a line
                line = file.readline().rstrip('\x0D').strip(':')
                if not line:
                    break
                # check if the line introduces new DXCC (line is starting with character)
                # samples:
                # Switzerland:              14:  28:  EU:   46.87:    -8.12:    -1.0:  HB:
                # Sicily:                   15:  28:  EU:   37.50:   -14.00:    -1.0:  *IT9:
                if line != '' and line[0].isalpha():
                    # split line by ':' and remove spaces
                    segments = [x.strip() for x in line.split(':')]
                    # check if last segment starts with '*'
                    # A “*” preceding this prefix indicates that the country is on the DARC WAEDC 
                    # list, and counts in CQ-sponsored contests, but not ARRL-sponsored contests
                    if segments[7][0] == '*':
                        # remove '*' and add a marker to country name
                        segments[7] = segments[7][1:]
                        segments[0] += ' (not DXCC)'
                    # store data in dict
                    cty_dict[segments[7]] = {'entity': segments[0], 'cq': int(segments[1]),
                                             'itu': int(segments[2]), 'continent': segments[3],
                                             'lat': float(segments[4]), 'long': float(segments[5]),
                                             'tz': -1*float(segments[6]), 'len': len(segments[7]),
                                             'primary_pfx': segments[7], 'exact_match': False}
                    # store country name, which is key of cty_dict for use with continued data
                    last = segments[7]

                # check if the line continues DXCC (line is starting with space)
                # samples:
                # IB9,ID9,IE9,IF9,II9,IJ9,IO9,IQ9,IR9,IT9,IU9,IW9,IY9,=II0GDF/9,=IQ1QQ/9,=IQ6KX/9,=IT9ACJ/I/BO,
                # =IT9YBL/SG,=IT9ZSB/LH,=IW0HBY/9;
                elif line != '' and line[0].isspace():
                    # remove spaces, trailing separators and split by ','
                    overrides = line.strip().rstrip(';').rstrip(',').split(',')
                    
                    for item in overrides:
                        # check if prefix/call is not already in dict
                        if item not in cty_dict.keys():
                            # get the already stored data from primary prefix
                            data = dict(cty_dict[last])
                            # apply regex to extract the prefix and overrides
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
                            if item.startswith('='):
                                data['exact_match'] = True
                            prefix = match.group("prefix")
                            cty_dict[prefix] = data
        self._data = cty_dict

    def update(self) -> bool:
        """Upates the instance's data from the feed.

        :raises Exception: If there is no date in the feed.
        :return: ``True`` if an update was done, otherwise ``False``.
        :rtype: bool
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

            if self._version == update_date:
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

        :getter: Returns version in ``YYYY-MM-DD`` format, or ``0000-00-00`` (if invalid date)
        :type: str
        """
        try:
            return datetime.strptime(self._version, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            return "0000-00-00"

    @property
    def version(self) -> str:
        """The version/date of the current BigCTY data.

        :getter: Returns version in ``YYYYMMDD`` format
        :type: str
        """
        return self._version

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
