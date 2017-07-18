''' Simple example of API usage.
	Just a walkthrough script.

	'''
# pylint: disable=C0103
import sys
from os import path
from time import sleep
sys.path.insert(0, path.abspath(".."))


# URL of the API.
remote_url = "https://liberles.cst.temple.edu/TAED/json/BLAST"
local_url = "http://127.0.0.1:5000/BLAST"

# Currently Version Mismatch with Remote server - will fix soon.
in_use_url = local_url

# This provides the object to call the API.
# Also can generate conditional clauses for DB searches, if you have the DB locally.
from TAED_API.TAEDSearch import BLASTSearch, BLASTStatus #pylint:disable=import-error,C0413

# First we'll do a simple blast search, with a simple sequence.
b_search = BLASTSearch(search={"e_value": 10, "max_hits": 50,
							"sequence": "MRPGIDSTDNAGRKGAAINANEAMLTAALLSCALLLALPATQGAQMGLAP"})
print(b_search.__dict__)
if not b_search.status["error_state"]:
	# Ready to run blast.
	print("\nOnce we've created the search object correctly, we can run the search remotely.")
	result = b_search.run_web_query(in_use_url)
	print("\nQuery Data:\n" + str(result.__dict__))

	# Early error.
	if result.status["error_state"]:
		print("\nSomething went wrong in the initial query.")
		print(result.status["error_message"])

	# We've got a started BLAST run.  Sleep while it is still running.
	while result.get_remote_status(in_use_url + "Status") == BLASTStatus.IN_PROGRESS:
		sleep(5)

	# If we're not complete, there's an issue somewhere.
	if result.get_remote_status(in_use_url + "Status") != BLASTStatus.COMPLETE:
		# Error!
		print("\nSomething went wrong.")
		print(result.get_remote_status(in_use_url + "Status"))
		print(result.__dict__)
		print(result.status["error_message"])
	else:
		print("\nWe're complete and have the XML for the BLAST result.")
		XML_DETAILS = result.get_remote_data(in_use_url + "Result")
		if XML_DETAILS['error_status'] is True:
			print("\nThere was an error:")
			print(XML_DETAILS['error_message'])
		else:
			for blastval in XML_DETAILS['blast_hits']:
				print(blastval.__dict__)
else:
	print("\nSome reported error.")
	print(b_search.status["error_state"])
