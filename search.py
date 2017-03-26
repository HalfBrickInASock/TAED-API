"""JSON API for searching TAED DB

    Functions:
    db_load_old -- Searches for records in old DB structure.
    dbLoadNew -- Searches for records in new DB structure.
    dict_dump -- Helper function that handles serialziation of search results.
    taed_search -- Handles search call.
    """

import json
import os
import sys
import logging
import urllib
import MySQLdb
import jsonpickle

from ruamel import yaml
from flask import Flask
from flask import request

import TAEDStruct
from TAEDSearch import TAEDSearch

APP = Flask(__name__)
CONF = yaml.safe_load(open('config.yaml', 'r+'))

def db_load_old(search_obj):
	"""Load records from the database (Old Structure) into a dictionary for handling and returning.

		Keyword Arguments:
		search_obj -- Object holding search data for the call.
		"""
	gene_dict = {}
	# pylint: disable=C0103
	log = logging.getLogger("dbserver")
	db = None
	try:
		db = MySQLdb.connect(host=CONF["db"]["host"], user=CONF["db"]["user"],
								passwd=CONF["db"]["pass"], db=CONF["db"]["old_db"])
		c = db.cursor(MySQLdb.cursors.DictCursor)

		# Conditional clause is built by search data; everything is covered in the two tables
		#	below in old format.
		from_clause, where_clause, parameters = search_obj.build_conditional()
		c.execute("SELECT DISTINCT baseDirectory, Directory, familyName" +
					", interleafed, nhxRooted, reconciledTree" +
					" FROM gimap " +
					" INNER JOIN taedfile ON gimap.taedFileNumber = taedfile.taedFileNumber" +
					from_clause + where_clause, parameters)
	except:
		gene_dict["error_state"] = True
		gene_dict["error_message"] = "There was an error getting your results from the db."
		log.error("DB Connection Problem: %s", sys.exc_info())
	try:
		print(c.rowcount)
		for gene in c:
			# Alignment / Tree info is stored in flat files in location given by db fields.
			path = os.path.join(CONF["flat_file"], gene["baseDirectory"], gene["Directory"])

			# Auto-load the files into our extensions of BioPython objects.
			gene_dict[gene["familyName"]] = {
				"Alignment":
					TAEDStruct.Alignment(
						os.path.join(path, gene["interleafed"])
						) if gene["interleafed"] != None else None,
				"Gene Tree":
					TAEDStruct.GeneTree(
						os.path.join(path, gene["nhxRooted"])
						) if gene["nhxRooted"] != None else None,
				"Reconciled Tree" :
					TAEDStruct.ReconciledTree(
						os.path.join(path, gene["reconciledTree"]))
			}
			gene_dict["familyNameLen"] = str(len(gene_dict[gene["familyName"]]["Alignment"].temp_return_alignment()))	# pylint: disable=C0301
		gene_dict["error_state"] = False
	except:
		gene_dict["error_state"] = True
		gene_dict["error_message"] = "There was an error with the data returned by the DB."
		log.error("Data Problem: %s", sys.exc_info())
	if db is not None:
		db.close()
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
		kegg_pathway -- Name of KEGG Pathway to filter for genes.
		"""
	# JSON does nothing at moment, will fix.
	user_data = request.get_json()
	if user_data is None:
		if request.method == 'POST':
			# This doesn't work, I'm not sure why.
			user_query = TAEDSearch(gi=request.form['gi_number'],
									species=request.form['species'],
									gene=request.form['gene'],
									min_taxa=request.form['min_taxa'],
									max_taxa=request.form['max_taxa'],
									kegg_pathway=request.form['kegg_pathway'])
		else:
			# GET does work.
			user_query = TAEDSearch(gi=request.args.get('gi_number', ''),
									species=urllib.parse.unquote_plus(request.args.get('species', '')),
									gene=urllib.parse.unquote_plus(request.args.get('gene', '')),
									min_taxa=request.args.get('min_taxa', ''),
									max_taxa=request.args.get('max_taxa', ''),
									kegg_pathway=urllib.parse.unquote_plus(request.args.get('kegg_pathway', '')))
	else:
		return user_data
	if user_query.error_state:
		return json.dumps(user_query.__dict__)

	return jsonpickle.encode(db_load_old(user_query))

if __name__ == "__main__":
	APP.run()
