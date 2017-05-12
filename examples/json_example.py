import json
import requests
import jsonpickle
# pylint: disable=C0103
import sys
from os import path
sys.path.insert(0, path.join(path.abspath("..")))

# This provides the object to call the API.
# Also can generate conditional clauses for DB searches, if you have the DB locally.
from TAED_API.TAEDSearch import TAEDSearch #pylint:disable=import-error

head = {"Content-type": "application/json"}
t_s = TAEDSearch(gi="349004")
ret = requests.post("http://vulpes/json/search", data={ 
		"gi_number" : "349004",
		"species" : "",
		"gene" : "",
		"min_taxa" : "",
		"max_taxa" : "",
		"kegg_pathway" : "",
		"dn_ds" : ""})
print(ret.status_code)
print(ret.reason)

ret = requests.post("http://vulpes/json/search", headers=head, data=jsonpickle.encode(t_s))
print(ret.status_code)
print(ret.reason)
print(ret.text)
