"""Object to handle TAED Searches.

    Classes:
    TAEDSearch -- Object handling data for a requested search.
	"""
from uuid import uuid4
import re
from os import path, stat
from io import StringIO
from enum import Enum
from numbers import Number
from Bio import SeqIO
from Bio.Blast import NCBIXML
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
import requests
import jsonpickle

import TAEDStruct

MAX_BLAST = 5

class BLASTStatus(Enum):
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

		Public Methods:
		build_blastall_params -- Builds list of parameters for blastall search.
		run_web_query -- Runs json query to remote service and returns result.
		"""
	__job_name = "BLAST Search"
	__sequences = []
	__e_value = None
	__max_hits = None
	__seq_re = re.compile(r"/^[ABCDEFGHIKLMNPQRSTUVWYZX\*\-\n\r]+$/i")
	__uid = None
	__remote_location = ""
	__target_files = []
	error_state = True
	error_message = "Unitialized"
	run_status = BLASTStatus.UNITIALIZED

	def __init__(self, job_name="BLAST Search", e_value="", max_hits="", #pylint: disable=too-many-arguments
					sequence="", file_data=None, file_name=""):
		self.__job_name = job_name
		self.__e_value = e_value
		self.__max_hits = max_hits
		self.__uid = uuid4()

		if not isinstance(e_value, Number):
			self.__error_message = "e_value must be a number."
			return
		if not isinstance(max_hits, Number):
			self.__error_message = "max_hits must be a number."
			return

		if sequence != "":
			if self.__seq_re.match(sequence) is None:
				self.error_message = "Submitted sequence is not a valid sequence."
				return
			else:
				t_seq = Seq(str(sequence))
				t_seqrec = SeqRecord(t_seq, id=self.__job_name)
				self.__sequences.append(t_seqrec)
		else:
			handle = None
			if file_data is not None:
				handle = StringIO.read(open(file_data))
			elif file_name is not None:
				handle = open(file_name, "rU")
			else:
				self.error_message = "A sequence or FASTA file must be sent."
				return
			for record in SeqIO.parse(handle, "fasta"):
				self.__sequences.append(record)
			handle.close()

		self.__error_state = False
		self.run_status = BLASTStatus.READY
		return

	def build_blastall_params(self, data_folder):
		"""Builds blastall command line arguments.
			"""
		parameter_list = []

		for i in range(self.__sequences):

			# "-i {0}".format(path.join(input_folder, uid + i)),
			self.__target_files.append(path.join(data_folder, "blasted", self.__uid + i))

			seq_param = [
				"-p blastp",
				"-d {0}".format(path.join(data_folder, "BLAST", "DATABASE99.fasta")),
				"-o {2}".format(self.__target_files[i]),
				"-a 2",
				"-m {0}".format(7) #XML Format
			]
			if self.__e_value != "":
				seq_param.append("-e {0}".format(self.__e_value))
			if self.__max_hits != "":
				seq_param.append("-v {0}".format(self.__max_hits))
			parameter_list.append(seq_param)
			if i >= MAX_BLAST:
				break

		return self.__sequences, parameter_list

	def get_local_status(self):
		files_made = 0
		for file_path in self.__target_files:
			if path.exists(file_path):
				if stat(file_path).st_size > 0:
					files_made += 1
		if files_made == len(self.__target_files) and files_made > 0:
			self.run_status = BLASTStatus.COMPLETE

		return self.run_status

	def get_remote_status(self):
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
		request_data = {}
		self.__remote_location = remote_url
		req = requests.get(remote_url, params=request_data)
		return jsonpickle.decode(req.text)

	def return_files(self):
		if self.run_status != BLASTStatus.COMPLETE:
			return {"error_status": True, "error_message": "BLAST Run Incomplete"}

		blast_hits = []
		for filename in self.__target_files:
			with open(filename) as handle:
				blast_hits.append(NCBIXML.read(handle))
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
	error_state = False
	error_message = None

	def __init__(self, gi="", species="", gene="",
					min_taxa="", max_taxa="", kegg_pathway=""):
		self.error_state = False
		self.error_message = None
		self.__gi = gi
		self.__species = species
		self.__gene = gene
		self.__kegg_pathway = kegg_pathway
		self.__min_taxa = min_taxa
		self.__max_taxa = max_taxa
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
		align_lengths = {}
		for gene in r_temp:
			if type(r_temp[gene]) is dict:
				r_temp[gene]["Alignment"].fix_bad_pickle()
		for key in align_lengths:
			r_temp[key] = align_lengths[key]

		return r_temp
