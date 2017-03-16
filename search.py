"""JSON API for searching TAED DB

    Functions:
    db_load_old -- Searches for records in old DB structure.
    dbLoadNew -- Searches for records in new DB structure.
    dict_dump -- Helper function that handles serialziation of search results.
    taed_search -- Handles search call.
    """

import json
import os
import MySQLdb
import jsonpickle
import sys
import logging

from flask import Flask
from flask import request

import TAEDStruct
from TAEDSearch import TAEDSearch

APP = Flask(__name__)
FLAT_FILE_PATH = "E:\\TAED"
DB_USER = "root"
DB_PASS	= ""

def db_load_old(search_obj, gene_dict):
	"""Load records from the database (Old Structure) into a dictionary for handling and returning.

		Keyword Arguments:
		search_obj -- Object holding search data for the call.
		gene_dict -- Dictionary to add search result data to.
		"""
	# pylint: disable=C0103
	log = logging.getLogger("dbserver")
	try:
		db = MySQLdb.connect(host="localhost", user=DB_USER, passwd=DB_PASS, db="TAED")
		c = db.cursor(MySQLdb.cursors.DictCursor)

		# Conditional clause is built by search data; everything is covered in the two tables
		#	below in old format.
		where_clause, parameters = search_obj.build_conditional()
		c.execute("SELECT * FROM gimap" +
					" INNER JOIN taedfile ON gimap.taedFileNumber = taedfile.taedFileNumber " +
					where_clause, parameters)
	except:
		gene_dict["error_state"] = True
		gene_dict["error_message"] = "There was an error getting your results from the db."
		log.error("DB Connection Problem: %s", sys.exc_info()[0])
	try:
		for i in range(0, c.rowcount):
			base = c.fetchone()
			# Alignment / Tree info is stored in flat files in location given by db fields.
			path = os.path.join(FLAT_FILE_PATH, base["baseDirectory"], base["Directory"])

			# Auto-load the files into our extensions of BioPython objects.
			gene_dict[base["familyName"]] = {
				"Alignment":
					TAEDStruct.Alignment(
						os.path.join(path, base["interleafed"])
						) if base["interleafed"] != None else None,
				"Gene Tree":
					TAEDStruct.GeneTree(
						os.path.join(path, base["nhxRooted"])
						) if base["nhxRooted"] != None else None,
				"Reconciled Tree" :
					TAEDStruct.ReconciledTree(
						os.path.join(path, base["reconciledTree"]))
			}
			gene_dict["familyNameLen"] = str(len(gene_dict[base["familyName"]]["Alignment"].temp_return_alignment()))	# pylint: disable=C0301
		gene_dict["error_state"] = False
	except:
		gene_dict["error_state"] = True
		gene_dict["error_message"] = "There was an error with the data returned by the DB."
		log.error("Data Problem: %s", sys.exc_info()[0])
	db.close()
	gene_dict["error_state"] = False
	return gene_dict

def db_load_new(search_obj, gene_dict):
	"""Load records from the database (Old Structure) into a dictionary for handling and returning.

		Keyword Arguments:
		search_obj -- Object holding search data for the call.
		gene_dict -- Dictionary to add search result data to.
		"""
	# Stub for now
	return False

@APP.route("/search", methods=['GET', 'POST'])
def taed_search():
	"""Search for records in the TAED DB, from GET or POST Parameters.

		Will return based on gi_number only, or all other parameters.
		gi_number, species, or gene is required.

		gi_number -- GI # of the gene to follow.

		Alternate Parameters:
		species -- Species name.
		gene -- Gene name.
		min_taxa -- Minimum # of taxa for gene.
		max_taxa -- Maximum # of taxa for gene.
		"""
	# JSON does nothing at moment, will fix.
	user_data = request.get_json()
	if user_data == None:
		if request.method == 'POST':
			# This doesn't work, I'm not sure why.
			user_query = TAEDSearch(gi=request.form['gi_number'],
									species=request.form['species'],
									gene=request.form['gene'],
									min_taxa=request.form['min_taxa'],
									max_taxa=request.form['max_taxa'])
		else:
			# GET does work.
			user_query = TAEDSearch(gi=request.args.get('gi_number', ''),
									species=request.args.get('species', ''),
									gene=request.args.get('gene', ''),
									min_taxa=request.args.get('min_taxa', ''),
									max_taxa=request.args.get('max_taxa', ''))
	else:
		return user_data
	if user_query.error_state:
		return json.dumps(user_query.__dict__)

	gene_dict = {}
	return jsonpickle.encode(db_load_old(user_query, gene_dict))

if __name__ == "__main__":
	APP.run()
