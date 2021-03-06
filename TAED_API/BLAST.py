"""@package TAED_API
	Runs BLAST searches against the TAED DB.
	Gets you XML objects of relevant genes / families to further investigate.

	Functions:
	run_blast -- Runs the actual BLAST search requested locally.
	blast_search -- Handles webservice call to run BLAST search.
	blast_status -- Handles call to check status of a previous BLAST search.
	blast_result -- Handles call to get BLAST search result.
	"""

from subprocess import Popen
from os import path, remove
from urllib.parse import urlencode
import sys
import logging

import jsonpickle
import requests
from ruamel import yaml
from flask import request, Response, safe_join, abort, send_file
from enum import Enum
from Bio import Phylo

from TAED_API.TAEDSearch import BLASTSearch, BLASTStatus

from TAED_API import APP

CONF = yaml.safe_load(open(path.join("config.yaml"), 'r+')) # "TAED_API",

LOG = logging.getLogger("BLASTQuery")


def run_blast(b_search):
	"""Runs a BLAST search using utility.

		Arguments:
		b_search -- Search data Object.
		"""

	try:
		seq_data, param_list = b_search.build_blastall_params(
			temp_folder=CONF["files"]["temp"], db_folder=CONF["files"]["blast"])
		blast_record = open(path.join(CONF["files"]["temp"], "blasted", "blastout.out"), 'a+')
		seq_run = []
	except FileNotFoundError:
		b_search.status = {
			"error_message": ("Remote server is having filesystem issues."
								" Please notify the system administrator."),
			"run_status": BLASTStatus.ERROR
		}

		return b_search

	b_search.status["run_status"] = BLASTStatus.IN_PROGRESS

	for i in range(len(seq_data)): #pylint:disable=consider-using-enumerate
		try:
			seq_run.append(Popen(["blastall"] + param_list[i], stdin=None, stdout=blast_record))
		except: #pylint:disable=bare-except
			b_search.status["run_status"] = BLASTStatus.ERROR
			b_search.status["error_message"] = str(sys.exc_info())

	return b_search

@APP.route("/BLAST", methods=['GET', 'POST'])
def blast_search():
	""" Does a BLAST search on TAED records.

		Parameters:
		job_name -- Name of BLAST Job
		sequence -- Protein Residue Sequence
		file -- Uploaded file with FASTA sequences; up to 5 will be used.
		e_value -- Threshold E Value.
		hits -- Maximum # of results to return.
		filters - JSON only.  Contains list of following:
			base - FilterBase Type Showing Type of Filter
			value - Value to Filter For
			field - Field to Filter On
			func - String name of filter function.
		"""
	user_query = None
	search = None
	resp = None

	if request.is_json:
		user_query = jsonpickle.decode(request.data)
	elif request.method == 'POST':
		if isinstance(request.data, bytes):
			user_query = jsonpickle.decode(request.data.decode())
			print("Decoded.")
		else:
			# All fields (but filters) required in POST (use empty string if you don't want them)
			user_query = {}
			for job_detail in ["job_name", "e_value", "max_hits", "dn_ds"]:
				if request.form[job_detail] != "":
					user_query[job_detail] = request.form[job_detail]

			for sequence_datatype in ["seq_obj", "sequence", "file_data", "file_name"]:
				if request.form[sequence_datatype] != "":
					user_query[sequence_datatype] = request.form[sequence_datatype]
					break # We only accept one sequence datatype.
	elif request.method == "GET":
		# GET Parameters are optional - only pass if you are using.
		user_query = {}
		for job_detail in ["job_name", "e_value", "max_hits", "dn_ds"]:
			if job_detail in request.args:
				user_query[job_detail] = request.args[job_detail]

		for sequence_datatype in ["seq_obj", "sequence", "file_data", "file_name"]:
			if sequence_datatype in request.args:
				user_query[sequence_datatype] = request.args[sequence_datatype]
				break # We only accept one sequence datatype.

	if isinstance(user_query, BLASTSearch):
		search = user_query
	elif isinstance(user_query, dict):
		search = BLASTSearch(user_query)
	else:
		resp = jsonpickle.encode({"error_message" : "Invalid Call Format", "run_status" : BLASTStatus.ERROR.value, "uid": None})

	if resp == None:
		new_blast = { "error_message" : "", "run_status" : BLASTStatus.ERROR.value, "uid": None }
		if not search.status["run_status"] == BLASTStatus.ERROR:
			search = run_blast(search)

			if not search.status["run_status"] == BLASTStatus.ERROR:
				uid = search.get_uid()
				with (open(path.join(CONF["files"]["temp"], "blasts", uid + ".bs"), mode="w")) as obj_file:
					json = jsonpickle.encode(search)
					LOG.error(json)
					obj_file.write(json)
				new_blast["uid"] = uid
			new_blast["run_status"] = search.status["run_status"].value
		
		if "error_message" in search.status:
			new_blast["error_message"] = search.status["error_message"]

		resp = jsonpickle.encode(new_blast)
	else:
		resp = jsonpickle.encode({"error_message" : "Invalid Call Format", "run_status" : BLASTStatus.ERROR.value, "uid": None})
	
	return resp

@APP.route("/BLASTStatus", methods=['GET', 'POST'])
def blast_status():
	""" Checks on the status of a previously run blast search.

		Parameters:
		uid -- Unique ID of previous search
		"""

	uid = None
	if request.is_json:
		uid = request.json["uid"]
	elif request.method == 'POST':
		uid = request.form["uid"]
	elif request.method == 'GET':
		uid = request.args.get('uid', '')
	else:
		return Response(jsonpickle.encode({"Bad Request" : request.data}), status=400, mimetype='application/json')

	# Need to handle different SHELF db formats.
	if (path.exists(path.join(CONF["files"]["temp"], "blasts", uid + ".bs")) or
			path.exists(path.join(CONF["files"]["temp"], "blasts", uid + ".bs.dat"))):
		status = BLASTStatus.ERROR
		try:
			with (open(path.join(CONF["files"]["temp"], "blasts", uid + ".bs"), mode="r")) as obj_file:
				# I should be using shelve but it is not working.
				temp = jsonpickle.decode(obj_file.read())
				status = temp.get_local_status()
			with (open(path.join(CONF["files"]["temp"], "blasts", uid + ".bs"), mode="w")) as obj_file:
				obj_file.write(jsonpickle.encode(temp))
			resp = jsonpickle.encode({"error_message": None, "run_status": status.value, "uid": uid})
		except (FileNotFoundError, FileExistsError):
			LOG.error(sys.exc_info())
			resp = jsonpickle.encode({"error_message" : sys.exc_info(), "run_status": BLASTStatus.ERROR.value, "uid": uid})			
	else:
		LOG.error("Status could not find path %s", path.join(CONF["files"]["temp"], "blasts", uid + ".bs"))
		resp = jsonpickle.encode({"error_message" : "No Record Found", "uid" : uid})

	return resp


@APP.route("/BLASTFile/<path:file_path>", methods=['GET', 'POST'])
def blast_file(file_path):
	if path.exists(safe_join(CONF["files"]["blast"], "runs", file_path)):
		return send_file(safe_join(CONF["files"]["blast"], "runs", file_path))
	else:
		return abort(404)

@APP.route("/BLAST/<path:file_path>", methods=['DELETE'])
def blast_remove(file_path):
	if path.exists(safe_join(CONF["files"]["blast"], "runs", file_path)):
		remove(safe_join(CONF["files"]["blast"], "runs", file_path))
		return Response(status=200)
	else:
		return abort(404)


@APP.route("/BLASTResult", methods=['GET', 'POST'])
def blast_result():
	""" Returns the results of a BLAST search.

		Parameters:
		uid -- Unique ID of previous search.
		"""
	uid = None
	resp = None
	if request.is_json:
		uid = request.json["uid"]
	elif request.method == 'POST':
		uid = request.form["uid"]
	elif request.method == 'GET':
		uid = request.args.get('uid', '')
	else:
		resp = jsonpickle.encode({"Invalid Request" : request.data})

	data = None
	if resp is None:
		# Need to handle different SHELF db formats.
		if (path.exists(path.join(CONF["files"]["temp"], "blasts", uid + ".bs")) or
				path.exists(path.join(CONF["files"]["temp"], "blasts", uid + ".bs.dat"))):

			# I should be using shelve but it is not working.
			with (open(path.join(CONF["files"]["temp"], "blasts", uid + ".bs"), mode="r")) as obj_file:
				temp = jsonpickle.decode(obj_file.read())
				status = temp.get_local_status()
			with (open(path.join(CONF["files"]["temp"], "blasts", uid + ".bs"), mode="w")) as obj_file:
				obj_file.write(jsonpickle.encode(temp))

			if status == BLASTStatus.COMPLETE:
				data = temp.return_files()
				final_data = []
				metadata = {}
				for hit in data:
					accession_list = [desc.accession for desc in hit.descriptions]
					req = requests.get(
						"{0}gene/list/species/geneName/alignment/gene tree/reconciled tree/".format(request.url_root), 
						data=",".join(accession_list))
					if req.status_code == 200:
						metadata.update(jsonpickle.decode(req.text))
					for gi in accession_list:
						if not gi in metadata:
							metadata[gi] = {}
						if not "search" in metadata[gi]:
							metadata[gi]["search"] = "{0}search?gi_number={1}".format(request.url_root, gi)
							metadata[gi]["genefamilies"] = "{0}genefamilies?gi_number={1}".format(request.url_root, gi)

					# Apply Filters.

					print("Pre:{0}:{1}".format(len(hit.descriptions), len(hit.alignments)))
					temp.prep_filters(metadata)
					hit.descriptions = temp.run_filters(hit.descriptions)
					hit.alignments = temp.run_filters(hit.alignments)
					print("Post:{0}:{1}".format(len(hit.descriptions), len(hit.alignments)))

				resp = jsonpickle.encode({"blast_hits" : data, "metadata": metadata, "uid": uid, "run_status": status.value})
			else:
				resp = jsonpickle.encode({"error_message" : "BLAST Not Complete", "uid" : uid, "run_status" : status.value})
		else:
			LOG.error("Return could not find path %s", path.join(CONF["files"]["temp"], "blasts", uid + ".bs"))
			resp = jsonpickle.encode({"error_message" : "No Record Found", "UID" : uid})

	return resp

if __name__ == "__main__":
	APP.run()
