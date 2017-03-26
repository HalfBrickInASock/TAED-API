# TAED API

API for TAED, The Adaptive Evolution Database. Work in progress.
Also provides python tools for calling it and handling the resulting data.
Python 3.x (3.5+ should definately work)

See examples directory for examples of tool usage in python.

Current API Calls Support:
	search.py
		Search as on the website; using gi number, gene, kegg pathway or species.
		(Latter three can be limited by min/max taxa)
		Returns files for alignment, gene tree, and reconciled tree.
		More detailed queries following.
	KEGG.py
		Returns list of KEGG pathways that can be used with search query.
	BLAST.py
		Runs BLAST search against TAED data.

Package Requirements:
	Local Call to Server [from TAEDSearch import TAEDSearch, BLASTSearch]
		requests (pip install requests)
			Used for calling the API if you want to use the search object.
		mysqlclient
			Python 3.6 MySQLDB drop-in replacement.
		jsonpickle (pip install jsonpickle)
			Used for easy JSON serialization / deserialization; inbuilt has limitations.
			Note: slightly buggy (though workaround in place)
		biopython (pip install biopython)
			Used for Sequence objects handled by BLAST.

	Server-Side Code [search.py / KEGG.py / BLAST.py]
		jsonpickle (pip install jsonpickle)
			Used for easy JSON serialization / deserialization; inbuilt has limitations.
		flask (pip install flask)
			Webservice framework.
		TAEDStruct.py
			Our biopython wrappers - will have more functionality soon.
		biopython (pip install biopython)
			Objects for handling biological data
		ruamel.yaml (pip install ruamel.yaml)
			Config file parsing.
		mysqlclient (pip install mysqlclient)
			Python 3.x mysqldb replacement.
		