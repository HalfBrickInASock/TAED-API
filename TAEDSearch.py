"""Object to handle TAED Searches.

    Classes:
    TAEDSearch -- Object handling data for a requested search.
	"""
import requests
import TAEDStruct
import jsonpickle

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
			request_data = {'gi_number':self.__gi}
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
