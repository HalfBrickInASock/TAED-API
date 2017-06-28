''' Test file that gets what the server sees as a post.

	'''

import sys
from os import path

import requests
import jsonpickle
# pylint: disable=C0103
sys.path.insert(0, path.join(path.abspath("..")))

# This provides the object to call the API.
# Also can generate conditional clauses for DB searches, if you have the DB locally.
from TAED_API.TAEDSearch import TAEDSearch, BLASTSearch, BLASTStatus #pylint:disable=import-error,C0413

remote_url = "http://127.0.0.1:5000/posteddata"

# We can successfully run a post and get back a json object holding a
#	dictionary with the results.
ret = requests.post("http://127.0.0.1:5000/postedform", data={
		"gi_number" : "349004",
		"species" : "",
		"gene" : "",
		"min_taxa" : "",
		"max_taxa" : "",
		"kegg_pathway" : "",
		"dn_ds" : ""})
request_sample = open("temp.txt", "w")
request_sample.write(ret.text)
request_sample.close()

# We can pass the whole object after configuration as well.
head = {"Content-type": "application/json"}
t_s = TAEDSearch(gi="349004", dn_ds=True)

ret = requests.post(remote_url, headers=head, data=jsonpickle.encode(t_s))
print(ret.status_code)
print(ret.reason)

handle = open("jr.txt", "w")
handle.write(ret.text)
handle.close()
ret = None

# BLAST Tests
b_search = BLASTSearch(e_value=10, max_hits=50,
						sequence="MRPGIDSTDNAGRKGAAINANEAMLTAALLSCALLLALPATQGAQMGLAP")
ret = requests.post(remote_url, headers=head, data=jsonpickle.encode(b_search))
print(ret.status_code)
print(ret.reason)


handle = open("blast.txt", "w")
handle.write(ret.text)
handle.close()
