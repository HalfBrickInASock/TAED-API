"""Runs BLAST searches against the TAED DB.
	Gets you XML objects of relevant genes / families to further investigate.

	Functions:
	run_blast -- Runs the actual BLAST search requested locally.
	blast_search -- Handles webservice call to run BLAST search.
	blast_status -- Handles call to check status of a previous BLAST search.
	blast_result -- Handles call to get BLAST search result.
	"""

from subprocess import Popen, PIPE
from os import path
import sys
import shelve
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

	seq_data, param_list = b_search.build_blastall_params(data_folder=CONF["flat_file"])
	blast_record = open(path.join(CONF["flat_file"], "blasted", "blastout.out"), 'a+')
	seq_run = []

	b_search.run_status = BLASTStatus.IN_PROGRESS

	for i in range(len(seq_data)): #pylint:disable=consider-using-enumerate
		try:
			seq_run.append(Popen(["blastall"] + param_list[i], stdin=PIPE, stdout=blast_record))
			seq_run[i].stdin.writelines(
				seq_data[i].Name.encode('utf-8'),
				str(seq_data[i].seq).encode('utf-8')
			)
			seq_run[i].stdin.close()
		except: #pylint:disable=bare-except
			b_search.run_status = BLASTStatus.ERROR
			b_search.error_message = str(sys.exc_info())

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
	if request.is_json:
		# JSON currently requires jsonpickle style encoding.
		# Will work to extend when I fix the class instantiation.
		user_query = jsonpickle.decode(request.data)
	elif request.method == 'POST':
		# All fields required in POST (default if you don't want them)
		user_query = BLASTSearch(sequence=request.form["sequence"],
									job_name=request.form["job_name"],
									file_data=request.form["file"],
									e_value=request.form["e_value"],
									max_hits=request.form["max_hits"])
	elif request.method == "GET":
		# GET.
		user_query = BLASTSearch(sequence=request.args.get('sequence', ''),
									job_name=request.args.get("job_name", 'BLAST Search'),
									file_data=request.args.get("file", ''),
									e_value=request.args.get("e_value", '1.0'),
									max_hits=request.args.get("max_hits", '50'))
	else:
		return request.data

	if not user_query.error_state:
		run_blast(user_query)
		uid = user_query.get_uid()
		status = user_query.get_local_status()

		with (open(path.join(CONF["flat_file"], "blasts", uid + ".bs"), mode="w")) as obj_file:
			json = jsonpickle.encode(user_query)
			LOG.error(json)
			obj_file.write(json)

		return jsonpickle.encode({uid : status})
	else:
		return jsonpickle.encode(user_query.__dict__)

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
		except:
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
