#!/usr/bin/python3
"""BLAST WSGI Setup.
	"""
import sys
import logging
from os import chdir, path
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, path.abspath(".."))
chdir(path.abspath(".."))

from BLAST import APP as application
