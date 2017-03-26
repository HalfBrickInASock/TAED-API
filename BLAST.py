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

import jsonpickle
from ruamel import yaml
from flask import Flask
from flask import request

from TAEDSearch import BLASTSearch, BLASTStatus

APP = Flask(__name__)
CONF = yaml.safe_load(open('config.yaml', 'r+'))

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
			seq_run[i].stdin.write(str(seq_data[i].seq).encode('utf-8'))
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
	# JSON does nothing at moment, will fix.
	user_data = request.get_json()
	if user_data is None:
		if request.method == 'POST':
			# This doesn't work, I'm not sure why.
			user_query = BLASTSearch(sequence=request.form["sequence"],
										job_name=request.form["job_name"],
										file_data=request.form["file"],
										e_value=request.form["e_value"],
										max_hits=request.form["max_hits"])
		else:
			# GET.
			user_query = BLASTSearch(sequence=request.args.get('sequence', ''),
										job_name=request.args.get("job_name", ''),
										file_data=request.args.get("file", ''),
										e_value=request.args.get("e_value", ''),
										max_hits=request.args.get("max_hits", ''))
	else:
		return user_data

	if not user_query.error_state:
		run_blast(user_query)
	else:
		return jsonpickle.encode(user_query.__dict__)
	return jsonpickle.encode(user_query.get_local_status())

@APP.route("/BLASTStatus", methods=['GET', 'POST'])
def blast_status():
	""" Checks on the status of a previously run blast search.

		Parameters:
		uid -- Unique ID of previous search
		"""
	# JSON does nothing at moment, will fix.
	user_data = request.get_json()
	if user_data is None:
		if request.method == 'POST':
			uid = request.form["uid"]
		else:
			uid = request.args.get('uid', '')
	else:
		return user_data

	if path.exists(path.join(CONF["flat_file"], "blasts", uid + ".bs")):
		search_shelf = shelve.open(path.join(CONF["flat_file"], "blasts", uid + ".bs"), writeback=True)
		status = search_shelf[uid].get_local_status()
		search_shelf[uid].sync()
		search_shelf.close()
		return status

@APP.route("/BLASTResult", methods=['GET', 'POST'])
def blast_result():
	""" Returns the results of a BLAST search.

		Parameters:
		uid -- Unique ID of previous search.
		"""
	# JSON does nothing at moment, will fix.
	user_data = request.get_json()
	if user_data is None:
		if request.method == 'POST':
			uid = request.form["uid"]
		else:
			uid = request.args.get('uid', '')
	else:
		return user_data

	if path.exists(path.join(CONF["flat_file"], "blasts", uid + ".bs")):
		search_shelf = shelve.open(path.join(CONF["flat_file"], "blasts", uid + ".bs"), writeback=True)
		if search_shelf[uid].get_local_status() == BLASTStatus.COMPLETE:
			data = search_shelf[uid].return_files()
		search_shelf[uid].sync()
		search_shelf.close()
	return jsonpickle.encode(data)

if __name__ == "__main__":
	APP.run()
