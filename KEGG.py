"""KEGG Pathway Search Module.

	Allows fetching the list of KEGG Pathnames that will work with JSON queries.
	"""
import sys
import logging

import jsonpickle
import MySQLdb

from ruamel import yaml
from flask import Flask
from flask import request

import TAEDStruct

APP = Flask(__name__)
CONF = yaml.safe_load(open('config.yaml', 'r+'))

def db_load_old():
	""" Get list of KEGG records into a dictionary for future use in searching."""
	# pylint: disable=C0103
	log = logging.getLogger("dbserver")
	db = None
	kegg_dict = {}
	try:
		db = MySQLdb.connect(host=CONF["db"]["host"], user=CONF["db"]["user"],
								passwd=CONF["db"]["pass"], db=CONF["db"]["old_db"])
		c = db.cursor(MySQLdb.cursors.DictCursor)

		# Conditional clause is built by search data; everything is covered in the two tables
		#	below in old format.
		c.execute("SELECT DISTINCT pathName FROM keggMap ORDER BY pathName")
		kegg_dict["path_names"] = list(c)
		kegg_dict["error_state"] = False
	except:
		kegg_dict["error_state"] = True
		kegg_dict["error_message"] = "There was an error getting your results from the db."
		log.error("DB Connection Problem: %s", sys.exc_info()[0])

	if db is not None:
		db.close()

	return kegg_dict

@APP.route("/KEGG", methods=['GET','POST'])
def kegg_search():
	"""Gets list of KEGG pathnames, returning a JSON object with list in 'path_names' """
	return jsonpickle.encode(db_load_old())

if __name__ == "__main__":
	APP.run()