from flask import Flask
APP = Flask(__name__)

import TAED_API.KEGG
import TAED_API.search
import TAED_API.BLAST