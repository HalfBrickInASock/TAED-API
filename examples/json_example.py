""" Example using JSON calls in python.
	"""
import sys
from os import path

import requests
import jsonpickle
# pylint: disable=C0103
sys.path.insert(0, path.join(path.abspath("..")))

# This provides the object to call the API.
# Also can generate conditional clauses for DB searches, if you have the DB locally.
from TAED_API.TAEDSearch import TAEDSearch #pylint:disable=import-error,C0413

remote_url = "https://liberles.cst.temple.edu/TAED/json/search"

# We can successfully run a post and get back a json object holding a
#	dictionary with the results.
ret = requests.post(remote_url, data={
		"gi_number" : "349004",
		"species" : "",
		"gene" : "",
		"min_taxa" : "",
		"max_taxa" : "",
		"kegg_pathway" : "",
		"dn_ds" : ""})
print("Let's see what we received:")
print(ret.status_code)	# HTTP Code 200
print(ret.reason)		# OK
post_result = jsonpickle.decode(ret.text)

# We can pass the whole object after configuration as well.
head = {"Content-type": "application/json"}
t_s = TAEDSearch(gi="349004", dn_ds=True)

ret = requests.post(remote_url, headers=head, data=jsonpickle.encode(t_s))
print(ret.status_code)
print(ret.reason)
json_result = jsonpickle.decode(ret.text)

handle = open("jr.txt")
handle.write(json_result)
handle.close()
