''' Simple example of API usage.
	Just a walkthrough script.

	'''
# pylint: disable=C0103
import sys
from os import path
sys.path.insert(0, path.abspath(".."))

# This provides the object to call the API.
# Also can generate conditional clauses for DB searches, if you have the DB locally.
from TAED_API.TAEDSearch import TAEDSearch #pylint:disable=import-error,C0413

# URL of the API.
remote_url = "https://liberles.cst.temple.edu/TAED/json/search"

# We can search for nothing, but it will get an error.
#  (Note: URL here is Flask local because API isn't available anywhere yet)
t_s = TAEDSearch()
result = t_s.run_web_query(remote_url)

print('Here is what happens when you search with no (or invalid) data:\n')

# You'll get a dictionary with an error message.  This should print out
#	"No Search Data; Please Pass gi_number, species, or gene"
if result["error_state"]:
	print(result["error_message"])

# You can see if your parameters are valid before calling by checking the search object.
if t_s.error_state:
	# There's an error!
	print(result["error_message"])

# Now for a valid search.
t_s = TAEDSearch(gi="349004")
result = t_s.run_web_query(remote_url)

if not result["error_state"]:
	# No error!
	# We've got a bunch of results and files, so let's explore our object.
	print('\nSo with real search, first level is the list of genes, as well as error info.\n')
	print(result.keys())

	for key in result:
		if isinstance(type(result[key]), dict):
			# Next level is the data we have for each gene.
			# Initially, it's just:
			#	Alignment, Reconciled Tree, Gene Tree.
			print(result[key].keys())

			print('\nWe can see each of those contains a TAEDStruct Class.\n')
			for subkey in result[key]:
				print(type(result[key][subkey]))

			# They hold flat file info, so they're pretty large on the whole.
			print(result[key]["Alignment"].temp_return_alignment())

			# We can save all of these to files.
			# Note: They have the same data as the files on the server but slightly
			#  different formatting due to BioPython load/save.
			# (Exception:  There may be some rounding done by BioPython)
			print("Saving to files, based on gene name.")
			for subkey in result[key]:
				print("Saving to " + key + "." + subkey)
				result[key][subkey].save_to_file(key + "." + subkey)
		else:
			print("\n" + key + ":" + str(result[key]))

# Try a KEGG search!
t_s = TAEDSearch(min_taxa="10", max_taxa="15", kegg_pathway="ABC transporters")
result = t_s.run_web_query(remote_url)

if not result["error_state"]:
	# No error!
	print("Kegg Search is going to get a lot more results.")
	print(result.keys())
else:
	print("Oops.")
	print(result)

# Now limit the KEGG search!
t_s = TAEDSearch(min_taxa="10", max_taxa="15", kegg_pathway="ABC transporters", dn_ds=True)
result = t_s.run_web_query(remote_url)

if not result["error_state"]:
	# No error!
	print("Should have fewer results this time.")
	print(result.keys())
else:
	print("Oops.")
	print(result)
