import sys
import requests
from io import StringIO
from os import path
from Bio import AlignIO
sys.path.insert(0, path.abspath(".."))

# This provides the object to call the API.
# Also can generate conditional clauses for DB searches, if you have the DB locally.
from TAED_API.TAEDSearch import TAEDSearch #pylint:disable=import-error,C0413

remote_url = "http://127.0.0.1:5050/"

# Get all results in agouti proteins that are under positive selection.
t_s = TAEDSearch(
	search={"dn_ds": "Y", "gene": "agouti"}
)
result = t_s.call_remote(remote_url, "genefamilies")

pdb_dict = {}
fasta_output = "output.fasta"

print(result)

if not result["status"]["error_state"]:
	# We can loop through the gene families returned.
	pdb_dict = {}
	fasta_output = "output.fasta"
	for gene in result["gene_families"]:
		# We can make a dictionary of PDBs and Gene Families.
		pdb_dict[result["gene_families"][gene]["protein family"]] = result["gene_families"][gene]["PDB"]
	
		# We can also grab all the alignments and stick them into a fasta file.
		# Here, get the alignment from the API.
		f = StringIO(requests.get(result["gene_families"][gene]["alignment"]).text)

		# Parse the alignment into a BioPython Alignment object, because we need to switch formats.
		alignment = AlignIO.read(f, "phylip")

		# Append the fasta version to file.
		with open(fasta_output, "a") as handle:
			AlignIO.write(alignment, fasta_output, "fasta")

print(pdb_dict)