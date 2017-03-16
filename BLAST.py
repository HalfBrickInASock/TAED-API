from flask import Flask
from flask import request

import TAEDStruct

APP = Flask(__name__)
@APP.route("/BLAST", methods=['GET', 'POST'])
def kegg_search():
	# Placeholder.
	return "API Not Yet Active"

if __name__ == "__main__":
	APP.run()
