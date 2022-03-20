=========
ctyparser
=========

A ``CTY.DAT`` parser for modern amateur radio programs.

Installation
============

``ctyparser`` requires Python 3.6 at minimum. Install by running::

    $ pip install ctyparser

License
=======

Copyright 2019-2022 classabbyamp, 0x5c

Released under the MIT License. See ``LICENSE`` for the full license text.

API
===

.. module:: ctyparser

.. autoclass:: BigCty

CLI Usage
=========

.. note:: CLI is a work in progress!

Currently, only updating/creating a file named ``cty.json`` in the current working directory is supported::

    $ python3 -m ctyparser
