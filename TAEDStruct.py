"""Classes for storing and manipulating phylogenetic data.

	Classes:
	ReconciledTree -- Handles reconciled gene/species tree data.
	Alignment -- Stores Multiple Sequence Alignment data.
	GeneTree -- Handles Gene Tree data.
	MixedTree -- Species tree reconciled to multiple gene trees w/ alignments.
	MixedClade -- Clade-level data structure used for MixedTree.
	"""

from Bio import Phylo
from Bio import AlignIO

class ReconciledTree(object):
	"""Stores and manipulates reconciled gene / species trees.

		Methods:
		import_from_file -- Loads tree from file in biopython-supported format.
		save_to_file -- Saves tree to file in biopython-supported  format.
		temp_return_local_tree -- Gets raw local tree data.  (Temporary Function until class is complete).
		build_mixed_tree -- Merges passed Reconciled Trees onto this to make MixedTree.
		visualize -- Builds a tree-structured visualition of alignments.
		"""
	__local_tree = None

	def __init__(self, file_name, file_format='newick'):
		""" Constructor.

			file_name -- Local filename to load from.
			file_format -- File format to load; use BioPython names.  'newick' default.
			"""
		self.import_from_file(file_name, file_format)

	def import_from_file(self, file_name, file_format='newick'):
		""" Loads Reconciled Tree from file.

			file_name -- Local filename to load from.
			file_format -- File format to load; use BioPython names.  'newick' default.
			"""
		self.__local_tree = Phylo.read(file_name, file_format)

	def save_to_file(self, file_name, file_format='newick'):
		""" Saves Reconciled Tree to file.

			file_name -- Local filename to save to.
			file_format -- File format to save as; use BioPython names.  'newick' default.
			"""
		Phylo.write(self.__local_tree, file_name, file_format)

	def temp_return_local_tree(self):
		""" Returns tree data (biopython object) for temporary test / dev purposes. """
		return self.__local_tree

	def build_mixed_tree(self, **kwargs):
		""" Merges passed Reconciled Trees onto this to make MixedTree.

			**kwargs -- List of ReconciledTrees to connect.
			"""
		for i in range(len(kwargs)):
			# Placeholder, just avoiding lint errors.
			return i and False

	def visualize(self, alignment):
		""" Creates a visualization with the given alignment, showing where things changed. """
		# Placeholder, just avoiding lint errors.
		return False and alignment

class Alignment(object):
	"""Stores and manipulates alignments.

		Methods:
		import_from_file -- Loads Alignment from file.
		save_to_file -- Saves Alignment to file.
		temp_return_alignment -- Gets BioPython alignment object.
		visualize -- Creates a visualization with the given alignment, showing where things changed.
		fix_bad_pickle -- Drops second half of local alignment to fix issues with serializer.
		"""
	__local_alignment = None

	def __init__(self, filename):
		""" Constructor.

			file_name -- Local filename to load from.
			file_format -- File format to load; use BioPython names.  'phylip' default.
			"""
		self.import_from_file(filename)

	def import_from_file(self, file_name, file_format='phylip'):
		""" Loads Alignment from file.

			file_name -- Local filename to load from.
			file_format -- File format to load; use BioPython names.  'phylip' default.
			"""
		self.__local_alignment = AlignIO.read(file_name, file_format)

	def save_to_file(self, file_name, file_format='phylip'):
		""" Saves Alignment to file.

			file_name -- Local filename to save to.
			file_format -- File format to save as; use BioPython names.  'phylip' default.
			"""
		AlignIO.write(self.__local_alignment, file_name, file_format)

	def temp_return_alignment(self):
		""" Returns alignment data (biopython object) for temporary test / dev purposes. """
		return self.__local_alignment

	def visualize(self):
		""" Creates a visualization with the given alignment, showing where things changed. """
		# Placeholder, just avoiding lint errors.
		return False

	def fix_bad_pickle(self):
		""" Drops second half of local alignment to fix issues with serializer. """
		self.__local_alignment = self.__local_alignment[:int(len(self.__local_alignment) / 2)]

class GeneTree(object):
	"""Stores and manipulates Gene Trees.

		Methods:
		import_from_file -- Loads tree from file in biopython-supported format.
		save_to_file -- Saves tree to file in biopython-supported  format.
		temp_return_local_tree -- Gets raw local tree data.  (Temporary Function until class is complete).
		add_alignment -- Displays alignment associated with tree, showing when/where it changed.
		"""
	__local_tree = None

	def __init__(self, filename):
		""" Constructor.

			file_name -- Local filename to load from.
			file_format -- File format to load; use BioPython names.  'newick' default.
			"""
		self.import_from_file(filename)

	def import_from_file(self, file_name, file_format='newick'):
		""" Loads Gene Tree from file.

			file_name -- Local filename to load from.
			file_format -- File format to load; use BioPython names.  'newick' default.
			"""
		self.__local_tree = Phylo.read(file_name, file_format)

	def save_to_file(self, file_name, file_format='newick'):
		""" Saves Gene Tree to file.

			file_name -- Local filename to save to.
			file_format -- File format to save as; use BioPython names.  'newick' default.
			"""
		Phylo.write(self.__local_tree, file_name, file_format)

	def temp_return_local_tree(self):
		""" Returns tree data (biopython object) for temporary test / dev purposes. """
		return self.__local_tree

	def add_alignment(self, alignment):
		""" Displays this gene's alignment alongside the tree.

			file_name -- Local filename to save to.
			file_format -- File format to save as; use BioPython names.  'newick' default.
			"""
		#Placeholder
		for record in alignment.temp_return_alignment():
			print(record.id)
		for term in self.__local_tree.get_terminals():
			print(term.name)

class MixedClade(Phylo.BaseTree.Clade):
	""" Clade Node holding data for multiple genes associated with organism.

		Interface Variables:
		organism -- Organism at this clade.
		genes -- List of genes reconciled to this clade.
		alignments -- List of alignments for the given genes.
		"""
	organism = ""
	genes = []
	alignments = {}

class MixedTree(object):
	"""Stores and manipulates species tree reconciled to mulitple genes.

		Methods:
		import_from_file -- Loads tree from file in biopython-supported format.
		save_to_file -- Saves tree to file in biopython-supported  format.
		temp_return_local_tree -- Gets raw local tree data.  (Temporary Function until class is complete).
		rebuild_multi_align -- This was going to have some purpose but I can't remember what.
		visualize -- Builds a tree-structured visualition of alignments.
		"""
	__local_tree = None

	def import_from_file(self, file_name, file_format='newick'):
		""" Loads Mixed Tree from file.

			file_name -- Local filename to load from.
			file_format -- File format to load; use BioPython names.  'newick' default.
			"""
		self.__local_tree = Phylo.read(file_name, file_format)

	def save_to_file(self, file_name, file_format='newick'):
		""" Saves Mixed Tree to file.

			file_name -- Local filename to save to.
			file_format -- File format to save as; use BioPython names.  'newick' default.
			"""
		Phylo.write(self.__local_tree, file_name, file_format)

	def temp_return_local_tree(self):
		""" Returns tree data (biopython object) for temporary test / dev purposes. """
		return self.__local_tree

	def rebuild_multi_align(self, file_name):
		""" This was going to have some purpose but I can't remember what. """
		# Placeholder
		return file_name and False

	def visualize(self):
		""" Creates a visualization of the entire tree, depicting associated genes / sequences. """
		#Placeholder
		return False
