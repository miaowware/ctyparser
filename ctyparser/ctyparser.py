#!/usr/bin/env python3
"""
Generates JSON from a CTY.DAT file

Format:
entity name: CQ Zone: ITU Zone: Continent: Latitude: Longitude: Time Zone: Primary Prefix:
    other,prefixes,and,=callsigns;
"""

import os
from datetime import datetime
import re
import json
import zipfile

import requests
import feedparser


def gen_cty_json():
    try:
        old_cty = json.load(open('resources/cty.json'))['last_updated']
    except:
        old_cty = None
        print('Missing/Broken cty.json')

    try:
        feed = feedparser.parse('http://www.country-files.com/category/big-cty/feed/')
        update_url = feed.entries[0]['link']
        date_str = re.search(r'(\d{2}-\w+-\d{4})', update_url).group(1).title()
        update_date = datetime.strftime(datetime.strptime(date_str, '%d-%B-%Y'), '%Y%m%d')
    except:
        print('Error parsing URL or feed')

    if old_cty == update_date:
        print('Already up-to-date')
        return False

    try:
        dl_url = f'http://www.country-files.com/bigcty/download/bigcty-{update_date}.zip'
        rq = requests.get(dl_url)
        with open('cty.zip', 'wb') as downloaded_file:
            downloaded_file.write(rq.content)
        with zipfile.ZipFile('cty.zip') as cty_zip:
            try:
                cty_zip.extract('cty.dat')
            except:
                print('Couldn\'t extract cty.dat')
        os.remove('cty.zip')
    except:
        print('Error retrieving new cty.dat')

    with open('cty.dat') as ctyfile:
        cty = dict()

        cty['last_updated'] = update_date

        last = ''
        while True:
            line = ctyfile.readline().rstrip('\x0D').strip(':')
            if not line:
                break
            if line != '' and line[0].isalpha():
                line = [x.strip() for x in line.split(':')]
                if line[7][0] == '*':
                    line[7] = line[7][1:]
                    line[0] += ' (not DXCC)'
                cty[line[7]] = {'entity': line[0], 'cq': int(line[1]),
                                'itu': int(line[2]), 'continent': line[3],
                                'lat': float(line[4]), 'long': float(line[5]),
                                'tz': -1*float(line[6]), 'len': len(line[7])}
                last = line[7]

            elif line != '' and line[0].isspace():
                line = line.strip().rstrip(';').rstrip(',').split(',')
                for i in line:
                    if i not in cty.keys():
                        data = cty[last]
                        if re.search(r'\[(\d+)\]', i):
                            data['itu'] = int(re.search(r'\[(\d+)\]', i).group(1))
                        if re.search(r'\((\d+)\)', i):
                            data['cq'] = int(re.search(r'\((\d+)\)', i).group(1))
                        if re.search(r'<(\d+)\/(\d+)>', i):
                            data['lat'] = float(re.search(r'<(\d+)/(\d+)>', i).group(2))
                            data['long'] = float(re.search(r'<(\d+)/(\d+)>', i).group(2))
                        if re.search(r'\{(\w+)\}', i):
                            data['continent'] = re.search(r'\{(\w+)\}', i).group(1)
                        if re.search(r'~(\w+)~', i):
                            data['tz'] = -1 * float(re.search(r'\{(\w+)\}', i).group(1))
                        prefix = re.sub(r'=?([^\(\[]*)(\(\d+\))?(\[\d+\])?(<\d+\/\d+>)?(\{\w+\})?(~\w+~)?', r'\1', i)
                        cty[prefix] = data
    with open('resources/cty.json', 'w') as cty_json:
        json.dump(cty, cty_json)

    os.remove('cty.dat')
    return True


if __name__ == '__main__':
    status = gen_cty_json()
    print(status)
