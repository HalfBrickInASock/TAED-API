# pylint: disable=C0413
"""@package TAED_API
	Core module init file.  Configured for Flask.
	"""
from flask import Flask
from flask_cors import CORS
APP = Flask(__name__)
CORS(APP)

import TAED_API.KEGG
import TAED_API.search
import TAED_API.BLAST
