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
from os import path
import sys
import logging

import jsonpickle
from ruamel import yaml
from flask import request

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
		seq_data, param_list = b_search.build_blastall_params(data_folder=CONF["flat_file"])
		blast_record = open(path.join(CONF["flat_file"], "blasted", "blastout.out"), 'a+')
		seq_run = []
	except FileNotFoundError:
		b_search.status = {
			"error_state": True,
			"error_message": ("Remote server is having filesystem issues."
								" Please notify the system administrator."),
			"run_status": BLASTStatus.ERROR
		}
		return b_search

	b_search.run_status = BLASTStatus.IN_PROGRESS

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
		"""
	user_query = None
	search = None

	if request.is_json:
		user_query = jsonpickle.decode(request.data)
	elif request.method == 'POST':
		# All fields required in POST (use empty string if you don't want them)
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
		return jsonpickle.encode({"error" : "Invalid Call Format"})

	if not search.status["error_state"]:
		search = run_blast(search)

		if not search.status["error_state"]:
			uid = search.get_uid()
			with (open(path.join(CONF["flat_file"], "blasts", uid + ".bs"), mode="w")) as obj_file:
				json = jsonpickle.encode(search)
				LOG.error(json)
				obj_file.write(json)

	return jsonpickle.encode(search)

@APP.route("/BLASTStatus", methods=['GET', 'POST'])
def blast_status():
	""" Checks on the status of a previously run blast search.

		Parameters:
		uid -- Unique ID of previous search
		"""

	uid = None
	if request.is_json:
		# No reason for JSON here
		return request.data
	elif request.method == 'POST':
		uid = request.form["uid"]
	elif request.method == 'GET':
		uid = request.args.get('uid', '')
	else:
		return jsonpickle.encode({"Invalid Request" : request.data})

	# Need to handle different SHELF db formats.
	if (path.exists(path.join(CONF["flat_file"], "blasts", uid + ".bs")) or
			path.exists(path.join(CONF["flat_file"], "blasts", uid + ".bs.dat"))):
		status = BLASTStatus.ERROR
		try:
			with (open(path.join(CONF["flat_file"], "blasts", uid + ".bs"), mode="r")) as obj_file:
				# I should be using shelve but it is not working.
				temp = jsonpickle.decode(obj_file.read())
				status = temp.get_local_status()
			with (open(path.join(CONF["flat_file"], "blasts", uid + ".bs"), mode="w")) as obj_file:
				obj_file.write(jsonpickle.encode(temp))
		except (FileNotFoundError, FileExistsError):
			LOG.error(sys.exc_info())
			return jsonpickle.encode({"Error" : sys.exc_info()})

		return jsonpickle.encode(status)
	else:
		LOG.error("Status could not find path %s", path.join(CONF["flat_file"], "blasts", uid + ".bs"))
		return jsonpickle.encode({"Error" : "No Record Found", "UID" : uid})

@APP.route("/BLASTResult", methods=['GET', 'POST'])
def blast_result():
	""" Returns the results of a BLAST search.

		Parameters:
		uid -- Unique ID of previous search.
		"""
	uid = None
	if request.is_json:
		# No reason for JSON here
		return request.data
	elif request.method == 'POST':
		uid = request.form["uid"]
	elif request.method == 'GET':
		uid = request.args.get('uid', '')
	else:
		return jsonpickle.encode({"Invalid Request" : request.data})

	data = None
	# Need to handle different SHELF db formats.
	if (path.exists(path.join(CONF["flat_file"], "blasts", uid + ".bs")) or
			path.exists(path.join(CONF["flat_file"], "blasts", uid + ".bs.dat"))):

		# I should be using shelve but it is not working.
		with (open(path.join(CONF["flat_file"], "blasts", uid + ".bs"), mode="r")) as obj_file:
			temp = jsonpickle.decode(obj_file.read())
			status = temp.get_local_status()
		with (open(path.join(CONF["flat_file"], "blasts", uid + ".bs"), mode="w")) as obj_file:
			obj_file.write(jsonpickle.encode(temp))

		if status == BLASTStatus.COMPLETE:
			data = temp.return_files()
		else:
			return jsonpickle.encode({"Error" : "BLAST Not Complete", "uid" : uid, "Status" : status})
	else:
		LOG.error("Return could not find path %s", path.join(CONF["flat_file"], "blasts", uid + ".bs"))
		return jsonpickle.encode({"Error" : "No Record Found", "UID" : uid})
	return jsonpickle.encode(data)

if __name__ == "__main__":
	APP.run()
