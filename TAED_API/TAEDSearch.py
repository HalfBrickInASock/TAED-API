"""Object to handle TAED Searches.

    Classes:
    TAEDSearch -- Object handling data for a requested search.
	"""
from uuid import uuid4
import re
import sys
import logging
from os import path, stat
from io import StringIO
from enum import Enum
from Bio import SeqIO
from Bio.Blast import NCBIXML
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
import requests
import jsonpickle

MAX_BLAST = 5

class BLASTStatus(Enum):
	"""Enum for status of BLAST run.
		"""
	ERROR = -1,
	UNITIALIZED = 0,
	READY = 1,
	IN_PROGRESS = 2,
	COMPLETE = 4

class BLASTSearch(object):
	"""Object holding blast search data.

		Interface Variables:
		error_state -- Whether search data currently held is in error or not.
		error_message -- Details on error related to current search data (if any).
		run_status -- Status of the BLAST runs.

		Public Methods:
		build_blastall_params -- Builds list of parameters for blastall search.
		run_web_query -- Runs json query to remote service and returns result.

		Setup Parameters:
		uuid -- Unique ID for the run (in case you have one already).
		job_name -- Name for the run.
		e_value -- E-Value Threshold for BLAST hits.
		max_hits -- Maximum number of hits to display.

		Sequence Parameters (send one):
		Only one is looked at; priority is order below.
		seq_obj -- Biopython object
		sequence -- Sequence string
		file_data -- Object holding file contents.
		file_name -- Name of a file (useful locally).
		"""
	__job_name = "BLAST Search"
	__run_count = 0
	__sequences = []
	__e_value = None
	__max_hits = None
	__seq_re = re.compile(r"^[ABCDEFGHIKLMNPQRSTUVWYZX\*\-\n\r]+$")
	__uid = None
	__data_folder = ""
	__remote_location = ""
	__dn_ds_filter = False
	error_state = True
	error_message = "Unitialized"
	run_status = BLASTStatus.UNITIALIZED

	def __init__(self, uuid=None, job_name="BLAST Search", e_value="1.0", max_hits="50", #pylint: disable=too-many-arguments
					dn_ds="N", seq_obj=None, sequence="", file_data=None, file_name=""):
		self.__job_name = job_name
		self.__uid = uuid
		self.error_state = True
		if self.__uid is None:
			self.__uid = str(uuid4())

		if file_data == "": file_data = None

		if dn_ds == "Y": self.__dn_ds_filter = True

		log = logging.getLogger("BLAST-Search")
		log.error("e_value: %s max_hits: %s", e_value, max_hits)

		try:
			self.__e_value = float(e_value)
			self.__max_hits = int(max_hits)
		except ValueError:
			self.error_message = "Invalid Numeric Parameters (e_value / max_hits):"
			return

		if seq_obj is not None:
			try:
				# Needs to be a list of Sequence Records
				self.__sequences = jsonpickle.decode(seq_obj)
			except ValueError:
				self.error_message = "Invalid Sequence Object: {0}".format(sys.exc_info())
				return
		elif sequence != "":
			if self.__seq_re.match(sequence) is None:
				self.error_message = "Submitted sequence (" + sequence + ") is not a valid sequence."
				return
			else:
				t_seq = Seq(str(sequence))
				t_seqrec = SeqRecord(t_seq, id=self.__job_name)
				self.__sequences.append(t_seqrec)
		else:
			handle = None
			if file_data is not None:
				handle = StringIO.read(open(file_data))
			elif file_name != "":
				handle = open(file_name, "rU")
			else:
				self.error_message = "A sequence or FASTA file must be sent."
				return
			for record in SeqIO.parse(handle, "fasta"):
				self.__sequences.append(record)
			handle.close()

		self.error_state = False
		self.run_status = BLASTStatus.READY
		self.__run_count = len(self.__sequences)
		return

	def get_uid(self):
		"""Gets unique identifier for this object.
			"""
		return self.__uid

	def build_blastall_params(self, data_folder):
		"""Builds blastall command line arguments.

			Parameters:
			data_folder -- Root folder for flat file manipulation (output, BLAST db, etc).
			"""
		parameter_list = []
		self.__data_folder = data_folder

		for i in range(len(self.__sequences)):

			# "-i {0}".format(path.join(input_folder, uid + i)),
			file_path = path.join(data_folder, "blasted", str(self.__uid) + "_" + str(i))

			seq_param = [
				"-p", "blastp",
				"-d", "{0}".format(path.join(data_folder, "BLAST", "DATABASE99.fasta")),
				"-o", "{0}".format(file_path),
				"-a2",
				"-m7" #XML Format
			]
			seq_param.append("-e{0}".format(self.__e_value))
			seq_param.append("-v{0}".format(self.__max_hits))
			parameter_list.append(seq_param)
			if i >= MAX_BLAST:
				break

		return self.__sequences, parameter_list

	def get_local_status(self):
		"""Gets status of a blast run acting locally.

			Return:
				BLASTStatus enum holding status.
			"""
		if self.error_state:
			return BLASTStatus.ERROR

		files_made = 0
		for i in range(0, self.__run_count):
			file_path = path.join(self.__data_folder, "blasted", str(self.__uid) + "_" + str(i))
			if path.exists(file_path):
				if stat(file_path).st_size > 0:
					files_made += 1

		if files_made == self.__run_count and files_made > 0:
			self.run_status = BLASTStatus.COMPLETE

		return self.run_status

	def get_remote_status(self):
		"""Gets status of a BLAST run on the remote server associated with this search.

			Return:
				BLASTStatus enum holding status.
			"""
		if self.error_state:
			return BLASTStatus.ERROR

		req = requests.get(self.__remote_location, params={"uid" : self.__uid})
		self.run_status = jsonpickle.decode(req.text)
		return self.run_status

	def run_web_query(self, remote_url):
		"""Queries remote webservice with data for BLAST search to get JSON result.

			Keyword Arguments:
				remote_url -- URL of webservice to call.

			Return:
				JSON Object holding a dictionary of returned data (including files).
			"""
		# Placeholder
		print(str(self.__sequences[0].seq))
		request_data = {
			"job_name": self.__job_name,
			"uuid": self.__uid,
			"e_value": self.__e_value,
			"max_hits": self.__max_hits,
			"sequence": str(self.__sequences[0].seq)
		}
		print(request_data)
		self.__remote_location = remote_url
		req = requests.get(remote_url, params=request_data)
		print(req)
		return jsonpickle.decode(req.text)

	def return_files(self):
		"""Gets final result of BLAST runs.

			Return:
				Dictionary with error status and (if successful) a list of NCBIXML Biopython objects.
			"""
		if self.run_status != BLASTStatus.COMPLETE:
			return {"error_status": True, "error_message": "BLAST Run Incomplete"}

		blast_hits = []

		for i in range(0, self.__run_count):
			file_path = path.join(self.__data_folder, "blasted", str(self.__uid) + "_" + str(i))
			with open(file_path) as handle:
				for record in NCBIXML.parse(handle):
					blast_hits.append(record)
		return {"error_status": False, "blast_hits": blast_hits}

class TAEDSearch(object):
	"""Object holding user search data.

		Interface Variables:
		error_state -- Whether search data currently held is in error or not.
		error_message -- Details on error related to current search data (if any).

		Public Methods:
		build_conditional -- Builds conditional WHERE clause for an SQL query for search.
		run_web_query -- Runs json query to remote service and returns result.
		"""

	__gi = None
	__species = None
	__gene = None
	__min_taxa = None
	__max_taxa = None
	__kegg_pathway = None
	__p_selection_only = False
	error_state = False
	error_message = None

	def __init__(self, gi="", species="", gene="",
					min_taxa="", max_taxa="", kegg_pathway="", dn_ds=False):
		self.error_state = False
		self.error_message = None
		self.__gi = gi
		self.__species = species
		self.__gene = gene
		self.__kegg_pathway = kegg_pathway
		self.__min_taxa = min_taxa
		self.__max_taxa = max_taxa
		self.__p_selection_only = dn_ds
		if ((self.__gi != "") or
			(self.__species != "") or
			(self.__gene != "") or
			(self.__kegg_pathway != "")):
			if (((self.__min_taxa != "") and (not self.__min_taxa.isdigit())) or
				((self.__max_taxa != "") and (not self.__max_taxa.isdigit()))):
				self.error_state = True
				self.error_message = "Invalid Taxa Data (Non Numeric)"
		else:
			self.error_state = True
			self.error_message = "No Search Data; Please Pass gi_number, kegg_pathway, species, or gene"

	def build_conditional(self):
		"""Builds conditional WHERE clause for an SQL query for search.

			No parameters; builds should work in both old and new DB formats.
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
				parameters.append(self.__species)
			if self.__gene != "":
				cond += " AND (geneName LIKE %s)"
				parameters.append(self.__gene)
			if self.__kegg_pathway != "":
				from_clause += " INNER JOIN keggMap ON keggMap.gi = gimap.gi"
				cond += " AND (keggMap.pathName = %s)"
				parameters.append(self.__kegg_pathway)
			if (self.__min_taxa != "") or (self.__max_taxa != ""):
				cond += " AND (directory BETWEEN %s AND %s)"
				parameters.append(self.__min_taxa)
				parameters.append(self.__max_taxa)
			if self.__p_selection_only:
				cond += " AND (positiveRatio = 1)"
		return from_clause, cond, parameters

	def run_web_query(self, remote_url):
		"""Queries remote webservice with search data to get JSON result.

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
			if self.__min_taxa != "":
				request_data['min_taxa'] = self.__min_taxa
			if self.__max_taxa != "":
				request_data['max_taxa'] = self.__max_taxa
		# Alignments are doubled by jsonpickle for some reason.
		#  	Will need to address; now we have a bunch of extra steps to cleave properly.
		#TODO: Address JSON Pickle doubling in a better manner.
		req = requests.get(remote_url, params=request_data)
		r_temp = jsonpickle.decode(req.text)
		for gene in r_temp:
			if isinstance(r_temp[gene], dict):
				r_temp[gene]["Alignment"].fix_bad_pickle()


		return r_temp
