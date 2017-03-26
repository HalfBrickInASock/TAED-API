''' Simple example of API usage.
	Just a walkthrough script.

	'''
# pylint: disable=C0103
import sys
from os import path
sys.path.insert(0, path.abspath(".."))

# This provides the object to call the API.
# Also can generate conditional clauses for DB searches, if you have the DB locally.
from TAEDSearch import BLASTSearch #pylint:disable=import-error

# First we'll do a simple blast search, with a simple sequence.
b_search = BLASTSearch(e_value=10, max_hits=50,
						sequence="MRPGIDSTDNAGRKGAAINANEAMLTAALLSCALLLALPATQGAQMGLAP")
print(b_search.__dict__)
if not b_search.error_state:
	# Ready to run blast.
	print("Once we've created the search object correctly, we can run the search remotely.")
	result = b_search.run_web_query("http://127.0.0.1:5000/BLAST")
	print(result)

	# We've got a started BLAST run.
else:
	print("Some reported error.")
	print(b_search.error_state)
