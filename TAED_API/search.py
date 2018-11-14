"""@package TAED_API
	JSON API for searching TAED DB

    Functions:
    db_load_old -- Searches for records in old DB structure.
    dbLoadNew -- Searches for records in new DB structure.
    dict_dump -- Helper function that handles serialziation of search results.
    taed_search -- Handles search call.
    """

import json
import re
from os import path
from itertools import chain
import sys
import logging
import urllib
import MySQLdb
import jsonpickle

from ruamel import yaml
from flask import request, Response, abort, send_file, safe_join

from Bio import Phylo

from TAED_API.TAEDStruct import Alignment, GeneTree, ReconciledTree
from TAED_API.TAEDSearch import TAEDSearch

from TAED_API import APP

CONF = yaml.safe_load(open(path.join("config.yaml"), 'r+')) #"TAED_API",

def get_db_cursor(front_clause, search_obj, db_name, status_dict):
	log = logging.getLogger("dbserver")
	db = None
	c = None
	try:
		db = MySQLdb.connect(host=CONF["db"]["host"], user=CONF["db"]["user"],
								passwd=CONF["db"]["pass"], db=db_name)
		c = db.cursor(MySQLdb.cursors.DictCursor)

		# Conditional clause is built by search data; everything is covered in the two tables
		#	below in old format.
		from_clause, where_clause, parameters = search_obj.build_conditional()
		print(front_clause + from_clause + where_clause, parameters)

		c.execute(front_clause + from_clause + where_clause, parameters)

		if c.rowcount == 0:
			status_dict["status"] = {
				"error_state": True,
				"error_message": "There were no results for your query."
			}
	except:
		status_dict["status"] = {
			"error_state": True,
			"error_message": "There was an error getting your results from the db."
		}
		log.error("DB Connection Problem: %s", sys.exc_info())

	return db, c

def search_flatfiles(search_obj):
	"""Load flatfile gene / species into a dictionary for handling and returning.

		Keyword Arguments:
		search_obj -- Object holding search data for the call.
		"""
	gene_dict = {
		"status": {
			"error_state": False
		}
	}
	# pylint: disable=C0103
	log = logging.getLogger("dbserver")
	db, c = get_db_cursor(
		"SELECT DISTINCT baseDirectory, Directory, familyName, interleafed, nhxRooted, reconciledTree" +
		" FROM gimap" +
		" INNER JOIN taedfile ON gimap.taedFileNumber = taedfile.taedFileNumber",
		search_obj, CONF["db"]["old_db"], gene_dict)
	if not gene_dict["status"]["error_state"]:
		for gene in c:
			# Alignment / Tree info is stored in flat files in location given by db fields.
			flat_path = path.join(CONF["files"]["flat"], gene["baseDirectory"], gene["Directory"])

			# Auto-load the files into our extensions of BioPython objects.
			try:
				gene_dict[gene["familyName"]] = {
					"Alignment":
						Alignment(
							path.join(flat_path, gene["interleafed"])
							) if gene["interleafed"] else None,
					"Gene Tree":
						GeneTree(
							path.join(flat_path, gene["nhxRooted"])
							) if gene["nhxRooted"] else None,
					"Reconciled Tree" :
						ReconciledTree(
							path.join(flat_path, gene["reconciledTree"])
							) if gene["reconciledTree"] else None
				}
				if gene_dict[gene["familyName"]]["Alignment"] is not None:
					gene_dict["familyNameLen"] = \
						str(len(gene_dict[gene["familyName"]]["Alignment"].temp_return_alignment()))	# pylint: disable=C0301
				gene_dict["status"]["error_state"] = False
			except Phylo.NewickIO.NewickError:
				log.error("Data Problem: %s [%s %s %s]", sys.exc_info(),
				path.join(flat_path, gene["interleafed"]),
				path.join(flat_path, gene["nhxRooted"]),
				path.join(flat_path, gene["reconciledTree"]))
				gene_dict.pop(gene["familyName"], None)
			except FileNotFoundError:
				log.error("Data Problem: %s [%s %s %s]", sys.exc_info(),
					path.join(flat_path, gene["interleafed"]),
					path.join(flat_path, gene["nhxRooted"]),
					path.join(flat_path, gene["reconciledTree"]))
	if db is not None:
		db.close()
	return gene_dict

def search_genefamilies(search_obj, url_root):
	gene_dict = {
		"status": {
			"error_state": False
		}
	}
	# pylint: disable=C0103
	log = logging.getLogger("dbserver")
	db, c = get_db_cursor("SELECT REPLACE(familyName,'_',' ') AS 'protein family'" +
		", IF(LENGTH(IFNULL(interleafed,'')) > 0, CONCAT_WS('/',baseDirectory,directory,interleafed),NULL) AS alignment" +
		", IF(0LENGTH(IFNULL(interleafed,'')) > 0, REPLACE(CONCAT_WS('/',baseDirectory,directory,taedfile.taedFileNumber,'.taedView'),'/.','.'),NULL) AS alignViewable" +
		", IF(LENGTH(IFNULL(nhxRooted,'')) > 0, CONCAT(CONCAT_WS('/',baseDirectory,directory,nhxRooted),'&fn=',familyName),NULL) AS 'rooted tree'" +
		", IF(LENGTH(IFNULL(reconciledTree,'')) > 0, CONCAT_WS('/',baseDirectory,directory,reconciledTree),NULL) AS 'reconciled tree'" +
		", pValue" +
		", IF(pValue > 0.05,paml1RatioDNDS,NULL) AS 'single dN/dS'" +
		", IF(pdbEntry IS NOT NULL, CONCAT_WS('/',pdbEntry),NULL) AS 'PDB'" +
		", subtrees, paml1RatioDNDS, pValue, significant, taedfile.taedFileNumber, directory" +
		", keggPathways, keggNames, positiveRatio, famMapLine, mapPDBLine, branchMapSummary, dndsSummary" +
		" FROM gimap INNER JOIN taedfile ON gimap.taedFileNumber = taedfile.taedFileNumber",
		search_obj, CONF["db"]["old_db"], gene_dict) # keggMap is in conditional.
	if not gene_dict["status"]["error_state"]:
		gene_dict["gene_families"] = {}
		for gene_family in c:
			this_family = dict(gene_family)
			this_family["alignment"] = "{0}flat_file/{1}".format(url_root, gene_family["alignment"])
			this_family["alignViewable"] = "{0}flat_file/{1}".format(url_root, gene_family["alignViewable"])
			this_family["rooted tree"] = "{0}flat_file/{1}".format(url_root, gene_family["rooted tree"])
			this_family["reconciled tree"] = "{0}flat_file/{1}".format(url_root, gene_family["reconciled tree"])

			if gene_family["paml1RatioDNDS"] and gene_family["pValue"]:
				this_family["subtree_set"] = list(zip(
					[float(x) for x in gene_family["paml1RatioDNDS"].split("_")],
					[float(x) for x in gene_family["pValue"].split("_")],
					["{0}flat_file/{1}/{2}_{3}.RST{4}".format(url_root, gene_family["directory"], gene_family["taedFileNumber"], x + 1,
							"_1" if float(y) < 0.05 else "") 
						for x in range(0, int(gene_family["subtrees"]))
						for y in gene_family["pValue"].split("_")],
					["{0}flat_file/{1}/{2}.subTree_tree_{3}.paml{4}".format(url_root, gene_family["directory"], gene_family["taedFileNumber"], x + 1,
							"_rooted" if float(y) < 0.05 else "_1_ratio_rooted") 
						for x in range(0, int(gene_family["subtrees"]))
						for y in gene_family["pValue"].split("_")],
				))
			elif gene_family["paml1RatioDNDS"] and (gene_family["directory"] == 2):
				this_family["subtree_set"] = tuple(
					float(gene_family["paml1RatioDNDS"]),
					"{0}flat_file/2/{2}.paml_rooted".format(url_root, gene_family["taedFileNumber"], 1)
				)
				print(gene_family)
			else:
				this_family["subtree_set"] = []
			
			if gene_family["mapPDBLine"]:
				this_family["lineages"] = dict(zip(
					gene_family["mapPDBLine"].split(","),
					gene_family["famMapLine"].split(",")
				))
			else:
				this_family["lineages"] = {}
			

			if gene_family["mapPDBLine"]:
				this_family["kegg"] = dict(zip(
					gene_family["keggNames"].split("_"),
					["http://www.genome.jp/dbget-bin/www_bget?{0}".format(x) for x in gene_family["keggPathways"].split("_")]
				))
			else:
				this_family["kegg"] = {}

			if gene_family["dndsSummary"]:
				this_family["selection"] = dict(zip(
					str(gene_family["branchMapSummary"]).strip().split("##"),
					str(gene_family["dndsSummary"]).strip().split("##")
				))
			else:
				this_family["selection"] = {}
			
			gene_dict["gene_families"][gene_family["taedFileNumber"]] = this_family

	if db is not None:
		db.close()
	return gene_dict

@APP.route("/rawdata", methods=['POST'])
def raw_data():
	return request.get_data()

@APP.route("/rawheaders", methods=['POST'])
def raw_headers():
	return jsonpickle.encode(request.headers)

@APP.route("/genefamilies", methods=['GET', 'POST'])
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
	user_query = None
	search = None

	# Parse the arguments into a dictionary to pass to constructor.

	if request.is_json:
		user_query = jsonpickle.decode(request.data)
	elif request.method == 'POST':
		if isinstance(request.data, bytes):
			user_query = jsonpickle.decode(request.data.decode())
			print(request.data)
			print(user_query)
		user_query = {
			"letter": request.form['letter'] if 'letter' in request.form else '',
			"gi_number": request.form['gi_number'] if 'gi_number' in request.form else '',
			"species": request.form['species'] if 'species' in request.form else '',
			"gene": request.form['gene'] if 'gene' in request.form else '',
			"min_taxa": request.form['min_taxa'] if 'min_taxa' in request.form else '',
			"max_taxa": request.form['max_taxa'] if 'max_taxa' in request.form else '',
			"kegg_pathway": request.form['kegg_pathway'] if 'kegg_pathway' in request.form else '',
			"dn_ds": request.form['dn_ds'] if 'dn_ds' in request.form else ''
		}
	elif request.method == 'GET':
		user_query = {
			"letter": request.args.get('letter', ''),
			"gi_number": request.args.get('gi_number', ''),
			"species": urllib.parse.unquote_plus(request.args.get('species', '')),
			"gene": urllib.parse.unquote_plus(request.args.get('gene', '')),
			"min_taxa": request.args.get('min_taxa', ''),
			"max_taxa": request.args.get('max_taxa', ''),
			"kegg_pathway": urllib.parse.unquote_plus(request.args.get('kegg_pathway', '')),
			"dn_ds": request.args.get('dn_ds', '')
		}
	# With a dictionary, call constructor.
	# If an object already, just use that.
	# Otherwise, bad JSON.
	resp = None

	if isinstance(user_query, TAEDSearch):
		search = user_query
	elif isinstance(user_query, dict):
		search = TAEDSearch(user_query)
	else:
		resp = jsonpickle.encode({"error" : "Invalid Call Format"})
	print(search)

	if resp is not None:
		try:
			if search.status["error_state"]:
				resp = json.dumps(search.__dict__)
		except TypeError:
			resp = jsonpickle.encode({"error" : "JSON Format Invalid"})

	resource = request.base_url.split("/")[-1]
	if resource == "search":
		resp = jsonpickle.encode(search_flatfiles(search))
	elif resource == "genefamilies":
		resp = jsonpickle.encode(search_genefamilies(search, request.url_root))
	flask_resp = Response(resp)
	return flask_resp

if __name__ == "__main__":
	APP.run()

@APP.route('/flat_file/<path:file_path>', methods=['GET'])
def flat_file(file_path):
	if path.exists(CONF["files"]["flat"] + file_path):
		return send_file(safe_join(CONF["files"]["flat"], file_path))
	else:
		return abort(404)

def filepath_fetch(fields, param_dict, db_name):
	log = logging.getLogger("dbserver")
	db = None
	c = None

	db = MySQLdb.connect(host=CONF["db"]["host"], user=CONF["db"]["user"],
							passwd=CONF["db"]["pass"], db=db_name)
	c = db.cursor(MySQLdb.cursors.DictCursor)

	print([x if isinstance(x, list) else [x] for x in param_dict.values()])

	# param_dict is a dict of fieldname (key) and either a single or list of values.
	# Single fieldnames are direct equality checked; lists of values use IN
	# All parameters are quoted individually by mysqlclient - to do so, the dictionary values are
	#  flattened into a single list.
	c.execute("SELECT {0} FROM gimap INNER JOIN taedfile ON gimap.taedFileNumber = taedfile.taedFileNumber WHERE {1}".format(
			",".join(fields),
			"AND".join(["({0} = %s)".format(x) if not isinstance(param_dict[x], list) 
				else "({0} IN ({1}))".format(x, ("%s," * len(param_dict[x]))[:-1]) 
				for x in list(param_dict.keys())])), 	
		list(chain.from_iterable([x if isinstance(x, list) else [x] for x in param_dict.values()]))) 

	return db, c

def gene_db(fields, gi, db_name):
	log = logging.getLogger("dbserver")
	db = None
	c = None
	try:
		db = MySQLdb.connect(host=CONF["db"]["host"], user=CONF["db"]["user"],
								passwd=CONF["db"]["pass"], db=db_name)
		c = db.cursor(MySQLdb.cursors.DictCursor)

		c.execute("SELECT {0} FROM gimap WHERE gi IN ({1})".format(",".join(fields), ('%s,' * len(gi))[:-1]), gi)
	except:
		c = None
		log.error("DB Connection Problem: %s", sys.exc_info())

	return db, c
	

@APP.route('/gene/<gi>/<path:properties>', methods=['GET'])
def gene_info(gi, properties):
	file_properties = {
		"alignment": "IF(LENGTH(IFNULL(interleafed,'')) > 0, CONCAT_WS('/',baseDirectory,directory,interleafed),NULL) AS alignment",
		"gene tree": "IF(LENGTH(IFNULL(nhxRooted,'')) > 0, CONCAT(CONCAT_WS('/',baseDirectory,directory,nhxRooted),'&fn=',familyName),NULL) AS 'gene tree'",
		"reconciled tree": "IF(LENGTH(IFNULL(reconciledTree,'')) > 0, CONCAT_WS('/',baseDirectory,directory,reconciledTree),NULL) AS 'reconciled tree'"
	}
	res = {}
	if properties is not None:
		# Injection Check.  Gi Handled Later.
		pat = re.compile("[\'\"`]")
		if pat.search("properties"):
			return abort(404)

		# Expands out properties list and adds gi.
		property_list = properties.split("/")
		if property_list[0] == "all":
			property_list[0] = "*"
		else:
			if "gi" not in properties:
				property_list.append("gi")
			for file_property in ["alignment", "gene tree", "reconciled tree"]:
				if file_property in property_list:
					property_list.remove(file_property)
				else:
					del file_properties[file_property]
	else:
		return abort(404)

	# Parses gi into list if necessary.
	if gi is None:
		return abort(404)
	elif gi == "list":
		if request.is_json:
			gi_list = jsonpickle.decode(request.data)
		else:
			gi_list = [int(x) for x in request.data.decode('utf-8').split(",")]
	else:
		gi_list = [gi]

	# Get all the base gene properties.
	db, c = gene_db(property_list, gi_list, CONF["db"]["old_db"])
	if c is not None:
		for gene_detail in c:
			res[gene_detail.pop('gi')] = gene_detail
		c.close()
	db.close()

	# Gets the file links
	db, c = filepath_fetch(list(file_properties.values()) + ["gi"], 
							{ "gi": gi_list }, CONF["db"]["old_db"])
	if c is not None:
		for gene_links in c:
			for field, value in dict(gene_links).items():
				if value is None:
					gene_links.pop(field)
				else:
					if field != "gi":
						gene_links[field] = "{0}flat_file/{1}".format(request.url_root, value)
			if gene_links["gi"] not in res:
				res[gene_links.pop('gi')] = gene_links
			else:
				res[gene_links.pop('gi')].update(gene_links)
		c.close()
	db.close()

	return jsonpickle.encode(res)

def protein_db(fields, famMapID, db_name):
	log = logging.getLogger("dbserver")
	db = None
	c = None

	try:
		db = MySQLdb.connect(host=CONF["db"]["host"], user=CONF["db"]["user"],
								passwd=CONF["db"]["pass"], db=db_name)
		c = db.cursor(MySQLdb.cursors.DictCursor)

		parameters = []
		if famMapID is not None:
			parameters.append(famMapID)
			where_clause = " WHERE famMapId = %s" 

		c.execute("SELECT {0} FROM proteinViewer{1}".format(fields, where_clause if famMapID is not None else ""), 
			parameters)
	except:
		c = None
		log.error("DB Connection Problem: %s", sys.exc_info())

	return db, c

@APP.route('/protein/<family>/<data_req>', methods=['GET'])
@APP.route('/protein/<family>')
def protein_info(family, data_req="all"):
	if family == "all":
		family = None
	if data_req == "map":
		db, c = protein_db("mappedBranchStart, mappedBranchEnd, dNdS, familyName", family, "TAED2")
	elif data_req == "all":
		db, c = protein_db("*", family, "TAED2")
	elif data_req == "file":
		db, c = protein_db("pdbID", family, "TAED2")
		if c is None:
			return abort(500)
		if c.rowcount == 0:
			return abort(404)
		pdb, chain = protein["pdbID"].split("_")
		return send_file("{0}pdb/{1}.pdb".format(CONF["files"]["flat"], pdb))
	else:
		return abort(404)

	if c is None:
		return abort(500)
	if c.rowcount == 0:
		return abort(404)

	protein = dict(c)
	if "annotations" in protein:
		protein["annotations"] = protein["annotations"].split(",")
	if "indicies" in protein:
		protein["indices"] = protein["indicies"].split(",")
	if "changes" in protein:
		protein["changes"] = [int(x) for x in protein["changes"].split(",")]
	if "pdbID" in protein:
		protein["pdb"], protein["pdb_chain"] = protein["pdbID"].split("_")
		protein.pop("pdbID", None)
	
	c.close()
	db.close()

	return jsonpickle.encode(protein)