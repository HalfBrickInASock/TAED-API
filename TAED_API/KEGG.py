"""@package TAED_API
	KEGG Pathway Search Module.

	Allows fetching the list of KEGG Pathnames that will work with JSON queries.
	"""
import sys
import logging
from os import path

import jsonpickle
import MySQLdb

from ruamel import yaml

from TAED_API import APP

CONF = yaml.safe_load(open(path.join("config.yaml"), 'r+')) # "TAED_API",

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
		kegg_dict["status"] = {"error_state": False}
	except MySQLdb.Error: # pylint: disable=no-member
		kegg_dict["status"] = {
			"error_state": True,
			"error_message": "There was an error getting your results from the db."
		}
		log.error("DB Connection Problem: %s", sys.exc_info()[0])

	if db is not None:
		db.close()

	return kegg_dict

@APP.route("/KEGG", methods=['GET', 'POST'])
def kegg_search():
	"""Gets list of KEGG pathnames, returning a JSON object with list in 'path_names' """
	return jsonpickle.encode(db_load_old())

if __name__ == "__main__":
	APP.run()
