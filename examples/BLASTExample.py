''' Simple example of API usage.
	Just a walkthrough script.

	'''
# pylint: disable=C0103
import sys
from os import path
from time import sleep
sys.path.insert(0, path.abspath(".."))

# This provides the object to call the API.
# Also can generate conditional clauses for DB searches, if you have the DB locally.
from TAED_API.TAEDSearch import BLASTSearch, BLASTStatus #pylint:disable=import-error,C0413

# First we'll do a simple blast search, with a simple sequence.
b_search = BLASTSearch(e_value=10, max_hits=50,
						sequence="MRPGIDSTDNAGRKGAAINANEAMLTAALLSCALLLALPATQGAQMGLAP")
print(b_search.__dict__)
if not b_search.error_state:
	# Ready to run blast.
	print("Once we've created the search object correctly, we can run the search remotely.")
	result = b_search.run_web_query("http://127.0.0.1:5000/BLAST")
	print(result)

	# We've got a started BLAST run.  Sleep while it is still running.
	while b_search.get_remote_status() == BLASTStatus.IN_PROGRESS:
		sleep(5)

	# If we're not complete, there's an issue somewhere.
	if b_search.get_remote_status() != BLASTStatus.COMPLETE:
		# Error!
		print("Something went wrong.")
		print(b_search.error_message)
	else:
		print("We're complete and have the XML for the BLAST result.")
		XML_DETAILS = b_search.return_files()
		print(XML_DETAILS)
else:
	print("Some reported error.")
	print(b_search.error_state)
