#!/usr/local/www/taed/pyenv/bin/python3
#pylint: disable=exec-used,wrong-import-position

"""WSGI Config for TAEd API
	Loads python3 virtual environment, then imports and starts flask application.
	"""

ACTIVATE = '/usr/local/www/taed/pyenv/bin/activate_this.py'
with open(ACTIVATE) as file_:
    exec(file_.read(), dict(__file__=ACTIVATE))

import logging
import sys
from os import chdir, path

logging.basicConfig(stream=sys.stderr)
chdir(path.abspath("/usr/local/www/taed/"))

from flask import Flask
from TAED_API import APP as application

APP = Flask(__name__)
