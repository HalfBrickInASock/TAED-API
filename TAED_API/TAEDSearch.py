"""@package TAED_API
	Object to handle TAED Searches.

    Classes:
    TAEDSearch -- Object handling data for a requested search.
	"""
from uuid import uuid4
import re
import sys
from os import path, stat
from io import StringIO
from enum import Enum
from Bio import SeqIO, Phylo
from Bio.Blast import NCBIXML
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
import requests
import jsonpickle
import logging

from ruamel import yaml
if path.exists("config.yaml"):
	CONF = yaml.safe_load(open(path.join("config.yaml"), 'r+'))
else:
	CONF = {
		"defaults": {
			"max_hits": 50,
			"e_value" : 1.0,
			"max_blasts": 5
		}
	}

class BLASTStatus(Enum):
	"""Enum for status of BLAST run.
		"""
	ERROR = -1
	UNITIALIZED = 0
	READY = 1
	IN_PROGRESS = 2
	COMPLETE = 4

class FilterBase(Enum):
	CUSTOM = -2
	PASS = -1
	VALUE = 0
	TREE = 1

class ValidFilters(Enum):
	VALUE = "Value_Filter"
	TREE = "Tree_Filter"

	@classmethod
	def has_func(cls, value):
		return any(value == item.value for item in cls)

	def get_func(self):
		return globals()[self.value]

class BLASTFilter(object):

	def __init__(self, base = FilterBase.PASS, field = "", value = "", func = None):
		self.base = base
		self.field = field
		self.value = value
		self.core_func = func
	
	def prep(self, metadata, newfunc = None):
		self.metadata = metadata
		if newfunc is not None:
			temp = ValidFilters(newfunc)
			self.core_func = temp
		if self.base == FilterBase.CUSTOM:
			# Use the custom function as given.
			self.func = self.core_func
			return
		elif self.base == FilterBase.PASS:
			self.func = None
			return
		elif self.base == FilterBase.TREE:
			
			self.func = lambda x: self.core_func.get_func()(
				tree_url = self.metadata[x.accession][self.field],		# tree_url
				value = self.value										# value
			) if self.field in self.metadata[x.accession] else False
		elif self.base == FilterBase.VALUE:
			self.func = lambda x: self.func(
				item = x,												# item
				field = self.field,										# field
				value = self.value										# value
			)

def Value_Filter(item, field, value):
	return True

def Tree_Filter(tree_url, value):

	tree_stream = StringIO(requests.get(tree_url).text)
	trees = Phylo.parse(tree_stream, "newick")

	for tree in trees:
		element = tree.find_any(name=".*{0}.*".format(value))
		if element is not None:
			return True
	return False

class BLASTSearch(object):
	"""Object holding blast search data.

		Interface Variables:
		status -- Holds status information in a dictionary
			error_state -- Whether search data currently held is in error or not.
			error_message -- Details on error related to current search data (if any).
			run_status -- Status of the BLAST runs.

		Public Methods:
		build_blastall_params -- Builds list of parameters for blastall search.
		run_web_query -- Runs json query to remote service and returns result.

		Setup Parameters:
		uuid -- Unique ID for the run (in case you have one already).
		job_name -- Name for the run; ignored if fetched from file.
		e_value -- E-Value Threshold for BLAST hits.
		max_hits -- Maximum number of hits to display.

		Sequence Parameters (send one):
		Only one is looked at; priority is order below.
		seq_obj -- Biopython object
		sequence -- Sequence string
		file_data -- Object holding file contents.
		file_name -- Name of a file (useful locally).
		"""

	def __init__(self, search, paths=None):

		# Regular Expression for amino acid sequence.
		aa_seq = re.compile(r"^[ABCDEFGHIKLMNPQRSTUVWYZX\*\-\n\r]+$")

		# Instance Identification.
		self.__uid = search["uid"] if "uid" in search else str(uuid4())

		# Status Management
		self.status = {
			"error_message": "Unitialized",
			"run_status":  BLASTStatus.UNITIALIZED
		}

		# Location
		self.paths = paths if paths is not None else {}

		# Search Filtering.
		# Positive Selection filtering can be:
		#	positive only (dn_ds = True, Y, y)
		#	negative only (dn_ds = False, N, n)
		#	no filtering (dn_ds = anything else)
		# e_value and max_hits are basic, numeric BLAST parameters.
		self.__limits = {}
		if "dn_ds" in search:
			if search["dn_ds"] in ["Y", "y", "True"]:
				self.__limits["dn_ds_filter"] = True
			elif search["dn_ds"] in ["N", "n", "False"]:
				self.__limits["dn_ds_filter"] = False
		try:
			self.__limits["e_value"] = \
				float(search["e_value"]) if "e_value" in search else CONF["defaults"]["e_value"]
			self.__limits["max_hits"] = \
				int(search["max_hits"]) if "max_hits" in search else CONF["defaults"]["max_hits"]
		except ValueError:
			self.status["error_message"] = "Invalid Numeric Parameters (e_value / max_hits):"
			self.status["run_status"] = BLASTStatus.ERROR
			return

		# Handles Blast Sequence Object.
		if "seq_obj" in search:
			try:
				# Needs to be a list of Sequence Records
				if not isinstance(search["seq_obj"], list):
					search["seq_obj"] = jsonpickle.decode(search["seq_obj"])
				self.__sequences = search["seq_obj"]
			except ValueError:
				self.status["error_message"] = "Invalid Sequence Object: {0}".format(sys.exc_info())
				self.status["run_status"] = BLASTStatus.ERROR
				return
		elif "sequence" in search:
			if aa_seq.match(search["sequence"]) is None:
				self.status["error_message"] = \
					"Submitted sequence (" + search["sequence"] + ") is not a valid sequence."
				self.status["run_status"] = BLASTStatus.ERROR
				return

			t_seq = Seq(str(search["sequence"]))
			t_seqrec = SeqRecord(t_seq, id = search["job_name"] if "job_name" in search else "BLAST Search")
			self.__sequences = [t_seqrec]
		else:
			self.__sequences = []
			handle = None
			if "file_data" in search:
				handle = StringIO(search["file_data"])
			elif "file_name" in search:
				handle = open(search["file_name"], "rU")
			else:
				self.status["error_message"] = "A sequence or FASTA file must be sent."
				return
			for record in SeqIO.parse(handle, "fasta"):
				self.__sequences.append(record)
			handle.close()

		# Result Filters.
		self.__filters = []
		if "result_filters" in search:
			try:
				for result_filter in search["result_filters"]:
					if isinstance(result_filter, BLASTFilter):
						self.__filters.append(result_filter)
					else:
						self.__filters.append(BLASTFilter(
							FilterBase(result_filter["base"]),
							result_filter["field"],
							result_filter["value"],
							ValidFilters(result_filter["func"])
						))
			except ValueError:
				self.status["run_status"] = BLASTStatus.ERROR
				self.status["error_message"] = "Invalid Filters: {0}".format(sys.exc_info())
				return

		self.status = {
			"run_status": BLASTStatus.READY
		}
		return

	def add_filter(self, blast_filter):
		self.__filters.append(blast_filter)

	def prep_filters(self, metadata):
		for blast_filter in self.__filters:
			blast_filter.prep(metadata)
	
	def run_filters(self, dataset):
		final_set = dataset
		for blast_filter in self.__filters:
			print("Aloha:{0}:{1}".format(blast_filter.func, len(final_set)))
			final_set = filter(blast_filter.func, final_set)
		return list(final_set)

	def get_uid(self):
		"""Gets unique identifier for this object.
			"""
		return self.__uid

	def build_blastall_params(self, temp_folder, db_folder):
		"""Builds blastall command line arguments.

			Parameters:
			temp_folder -- Root folder for flat file manipulation (output, BLAST db, etc).
			"""
		parameter_list = []
		self.paths["out"] = path.join(db_folder, "runs")

		for i in range(len(self.__sequences)):

			output_path = path.join(self.paths["out"], str(self.__uid) + "_" + str(i) + ".blast")
			input_path = path.join(temp_folder, "blasts", str(self.__uid) + "_" + str(i) + ".fasta")
			SeqIO.write(self.__sequences[i], input_path, "fasta")

			seq_param = [
				"-p", "blastp",
				"-i", "{0}".format(input_path),
				"-d", "{0}".format(path.join(db_folder, "DATABASE99.fasta")),
				"-o", "{0}".format(output_path),
				"-a2",
				"-m7" #XML Format
			]
			seq_param.append("-e{0}".format(self.__limits["e_value"]))
			seq_param.append("-v{0}".format(self.__limits["max_hits"]))
			parameter_list.append(seq_param)

		return self.__sequences, parameter_list

	def get_local_status(self):
		"""Gets status of a blast run acting locally.

			Return:
				BLASTStatus enum holding status.
			"""
		if self.status["run_status"] == BLASTStatus.ERROR:
			return BLASTStatus.ERROR

		files_made = 0
		for i in range(0, len(self.__sequences)):
			file_path = path.join(self.paths["out"], str(self.__uid) + "_" + str(i) + ".blast")
			if path.exists(file_path):
				if stat(file_path).st_size > 0:
					files_made += 1

		if files_made == len(self.__sequences) and files_made > 0:
			self.status["run_status"] = BLASTStatus.COMPLETE

		return self.status["run_status"]

	def get_remote_status(self, remote_url=None):
		"""Gets status of a BLAST run on the remote server associated with this search.

			Return:
				BLASTStatus enum holding status.
			"""
		if self.status["run_status"] == BLASTStatus.ERROR:
			return BLASTStatus.ERROR

		if remote_url is None:
			remote_url = self.paths["remote"] + "Status"

		req = requests.get(remote_url, params={"uid" : self.__uid})
		self.status = jsonpickle.decode(req.text)
		self.status["run_status"] = BLASTStatus(self.status["run_status"])
		return self.status["run_status"]

	def get_remote_data(self, remote_url=None):
		"""Gets the data of a completed BLAST run.

			Return:
				Dictionary with error status and (if successful) a list of NCBIXML Biopython objects.
			"""
		if self.status["run_status"] == BLASTStatus.ERROR:
			return self.status

		if remote_url is None:
			remote_url = self.paths["remote"] + "Result"

		req = requests.get(remote_url, params={"uid" : self.__uid})
		return jsonpickle.decode(req.text)


	def run_web_query(self, remote_url):
		"""Queries remote webservice with data for BLAST search to get JSON result.

			Keyword Arguments:
				remote_url -- URL of webservice to call.

			Return:
				JSON Object holding a dictionary of returned data (including files).
			"""
		self.paths["remote"] = remote_url

		request_data = {
			"uid": self.__uid,
			"e_value": self.__limits["e_value"],
			"max_hits": self.__limits["max_hits"],
			"seq_obj": self.__sequences,
			"result_filters": self.__filters,
		}

		req = requests.post(remote_url, data=jsonpickle.encode(request_data))
		try:
			self.status = jsonpickle.decode(req.text)
			self.status.pop("uid")
		except TypeError:
			self.status = { "run_status": BLASTStatus.ERROR, "error_message": "Error {0} Parsing Response {1}".format(sys.exc_info(), req.text) }
		except AttributeError:
			self.status = { "run_status": BLASTStatus.ERROR, "error_message": "Error {0} Parsing Response {1}".format(sys.exc_info(), req.text) }

		return self

	def return_files(self):
		"""Gets final result of BLAST runs.

			Return:
				Dictionary with error status and (if successful) a list of NCBIXML Biopython objects.
			"""
		if self.status["run_status"] != BLASTStatus.COMPLETE:
			return {"run_status": self.status["run_status"], "error_message": "BLAST Run Incomplete" }

		blast_hits = []

		for i in range(0, len(self.__sequences)):
			file_path = path.join(self.paths["out"], str(self.__uid) + "_" + str(i) + ".blast")
			with open(file_path) as handle:
				# Will actually only make 1 blast hit because it blasted each sequence separately.
				# But that's ok, since parse only gives an iterator anyway.
				for record in NCBIXML.parse(handle):
					blast_hits.append(record)
		return blast_hits

class TAEDSearch(object):
	"""Object holding user search data.

		Interface Variables:
		status -- Object Status
			error_state -- Whether search data currently held is in error or not.
			error_message -- Details on error related to current search data (if any).

		Public Methods:
		build_conditional -- Builds conditional WHERE clause for an SQL query for search.
		run_web_query -- Runs json query to remote service and returns result.
		"""

	def __init__(self, search=None):
		self.status = {"error_state": False}

		if search is None:
			self.status = {
				"error_state": True,
				"error_message": "No Search Data; Please Pass gi_number, kegg_pathway, species, gene, or first character"
			}
			return

		# Basic Assignments from Dictionary
		self.__gi = search["gi_number"] if "gi_number" in search else ""
		self.__species = search["species"] if "species" in search else ""
		self.__gene = search["gene"] if "gene" in search else ""
		self.__kegg_pathway = search["kegg_pathway"] if "kegg_pathway" in search else ""
		self.__letter = search["letter"] if "letter" in search else ""

		# Parameters that restrict search space.
		self.__limits = {}
		if "min_taxa" in search:
			if search["min_taxa"].isdigit():
				self.__limits["min_taxa"] = search["min_taxa"]
			elif search["min_taxa"] != "":
				self.status = {
					"error_state": True,
					"error_message": "Invalid Taxa Data (Non Numeric)"
				}
		if "max_taxa" in search:
			if search["max_taxa"].isdigit():
				self.__limits["max_taxa"] = search["max_taxa"]
			elif search["max_taxa"] != "":
				self.status = {
					"error_state": True,
					"error_message": "Invalid Taxa Data (Non Numeric)"
				}

		# Selection filtering can be:
		#	positive only (dn_ds = True, Y, y)
		#	negative only (dn_ds = False, N, n)
		#	no filtering (dn_ds = anything else)
		if "dn_ds" in search:
			if search["dn_ds"] in ["Y", "y", "True"]:
				self.__limits["p_selection"] = True
			if search["dn_ds"]  in ["N", "n", "False"]:
				self.__limits["p_selection"] = False

		"""
		if ((self.__gi == "") and
			(self.__species == "") and
			(self.__gene == "") and
			(self.__kegg_pathway == "")):
			self.status = {
				"error_state": True,
				"error_message": "No Search Data; Please Pass gi_number, kegg_pathway, species, or gene"
			}
		"""

	def build_conditional(self):
		"""Builds conditional WHERE clause for an SQL query for search.

			No parameters.
			"""
		from_clause = ""
		cond = " WHERE (True)"
		parameters = []
		if self.__gi != "":
			cond += " AND (gi = %s)"
			parameters.append(self.__gi)
		else:
			if self.__species != "":
				cond += " AND (species LIKE %s)"
				parameters.append("%" + self.__species + "%")
			if self.__gene != "":
				cond += " AND (geneName LIKE %s)"
				parameters.append("%" + self.__gene + "%")
			if self.__kegg_pathway != "":
				from_clause += " INNER JOIN keggMap ON keggMap.gi = gimap.gi"
				cond += " AND (keggMap.pathName = %s)"
				parameters.append(self.__kegg_pathway)
			if self.__letter != "":
				if self.__letter.isdigit():
					cond += " LEFT(familyName,1) IN ('1','2','3','4','5','6','7','8','9','0') AND Complete = 1"
				else:
					cond += " AND familyName LIKE %s AND Complete = 1"
					parameters.append(self.__letter + "%")
			if "min_taxa" in self.__limits:
				if "max_taxa" in self.__limits:
					cond += " AND (directory BETWEEN %s AND %s)"
					parameters.append(self.__limits["min_taxa"])
					parameters.append(self.__limits["max_taxa"])
				else:
					cond += " AND (directory >= %s)"
					parameters.append(self.__limits["min_taxa"])
			elif "max_taxa" in self.__limits:
					cond += " AND (directory <= %s)"
					parameters.append(self.__limits["max_taxa"])
			if "p_selection" in self.__limits:
				if self.__limits["p_selection"]:
					cond += " AND (positiveRatio = 1)"
				else:
					cond += " AND (positiveRatio != 1)"
		return from_clause, cond, parameters

	def call_remote(self, remote, service):
		"""Calls any remote service with search data.

			Keyword Arguments:
				remote -- URL of remote webservice.
				service -- name of remote service to call.

			Return:
				JSON dictionary holding returned data.
			"""
		req = requests.post(remote + service, data = jsonpickle.encode(self))
		return jsonpickle.decode(req.text)

	def run_web_query(self, remote_url):
		"""Queries remote /search webservice with search data to get JSON sequences in return.

			Keyword Arguments:
				remote_url -- URL of webservice to call.

			Return:
				JSON Object holding a dictionary of returned data (including files).
			"""
		if self.__gi != "":
			request_data = {'gi_number': self.__gi}
		else:
			request_data = {}
			if self.__species != "":
				request_data['species'] = self.__species
			if self.__gene != "":
				request_data['gene'] = self.__gene
			if self.__kegg_pathway != "":
				request_data['kegg_pathway'] = self.__kegg_pathway
			if self.__letter != "":
				request_data['lettter'] = self.__letter
			if "min_taxa" in self.__limits:
				request_data['min_taxa'] = self.__limits["min_taxa"]
			if "max_taxa" in self.__limits:
				request_data['max_taxa'] = self.__limits["max_taxa"]
			if "p_selection" in self.__limits:
				request_data['dn_ds'] = self.__limits["p_selection"]
		# Alignments are doubled by jsonpickle for some reason.
		#  	Will need to address; now we have a bunch of extra steps to cleave properly.
		#TODO: Address JSON Pickle doubling in a better manner.
		req = requests.get(remote_url, params=request_data)

		r_temp = jsonpickle.decode(req.text)
		for gene in r_temp:
			if isinstance(r_temp[gene], dict):
				if "Alignment" in r_temp[gene]:
					r_temp[gene]["Alignment"].fix_bad_pickle()

		return r_temp
