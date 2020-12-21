"""
ctyparser commandline interface
---

Copyright 2019-2020 classabbyamp, 0x5c
Released under the terms of the MIT license.
"""


import ctyparser
# import argparse
import pathlib


file = pathlib.PurePath("./cty.json")
try:
    cty = ctyparser.BigCty(file)
except FileNotFoundError:
    cty = ctyparser.BigCty()
print("Updated:", cty.update())
print("Datestamp:", cty.formatted_version)
print("Version Entity:", cty.get("VERSION", "Not present, data possibly corrupted."))
cty.dump(file)
