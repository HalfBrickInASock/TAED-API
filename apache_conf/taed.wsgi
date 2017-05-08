#!/usr/bin/python3
import os
from flask import Flask
from TAED_API import APP

os.environ['TAED_CONFIG'] = '/usr/local/www/taed/application.cfg'

APP = Flask(__name__)
APP.config.from_object('TAED.default_config')
APP.config.from_envvar('TAED_CONFIG')