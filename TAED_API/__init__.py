# pylint: disable=C0413
"""@package TAED_API
	Core module init file.  Configured for Flask.
	"""
from flask import Flask
APP = Flask(__name__)

import TAED_API.KEGG
import TAED_API.search
import TAED_API.BLAST
