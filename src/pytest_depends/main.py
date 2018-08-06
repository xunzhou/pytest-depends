"""
A module to manage dependencies between pytest tests.

This module provides the methods implementing the main logic. These are used in the pytest hooks that are in
__init__.py.
"""

import collections

import networkx

from pytest_depends.constants import MARKER_NAME
from pytest_depends.constants import MARKER_KWARG_DEPENDENCIES
from pytest_depends.util import clean_nodeid
from pytest_depends.util import get_absolute_nodeid
from pytest_depends.util import get_names


class DependencyManager(object):
	""" Keep track of tests, their names and their dependencies. """

	def __init__(self):
		"""
		Create a new DependencyManager.

		Should not be used directly, get_instance() instead.
		"""
		self._items = None
		self._name_to_items = None
		self._results = None

	@classmethod
	def get_instance(cls):
		""" Get the instance of the singleton. """
		if not hasattr(cls, '_instance'):
			cls._instance = DependencyManager()
		return cls._instance

	@property
	def items(self):  # noqa: D401
		""" The collected tests that are managed by this instance. """
		if self._items is None:
			raise Exception('The items have not been set yet')
		return self._items

	@items.setter
	def items(self, items):
		if self._items is not None:
			raise Exception('The items have already been set')
		self._items = items

		# Build a map from name to test(s)
		self._name_to_items = collections.defaultdict(list)
		for item in items:
			names = get_names(item)
			for name in names:
				self._name_to_items[name].append(item)
		self._name_to_items.default_factory = None

	@property
	def name_to_items(self):  # noqa: D401
		""" A mapping from names to test(s). """
		assert self.items is not None
		return self._name_to_items

	def print_name_map(self, verbose):
		""" Print a human-readable version of the name -> test mapping. """
		print('Dependency names:')
		for name, name_items in sorted(self.name_to_items.items(), key = lambda x: x[0]):
			if len(name_items) == 1:
				nodeid = clean_nodeid(name_items[0].nodeid)
				if name == nodeid:
					# This is just the base name, only print this when verbose
					if verbose:
						print('  {name}'.format(**locals()))
				else:
					# Name refers to a single node id, so use the short format
					print('  {name} -> {nodeid}'.format(**locals()))
			else:
				# Name refers to multiple node ids, so use the long format
				print('  {name} ->'.format(**locals()))
				nodeids = [clean_nodeid(item.nodeid) for item in name_items]
				nodeids.sort()
				for nodeid in nodeids:
					print('    {nodeid}'.format(**locals()))

	@property
	def sorted_items(self):
		""" Get a sorted list of tests where all tests are sorted after their dependencies. """
		# Build a directed graph for sorting
		dag = networkx.DiGraph()

		# Insert all items as nodes, to prevent items that have no dependencies and are not dependencies themselves from
		# being lost
		dag.add_nodes_from(self.items)

		# Insert edges for all the dependencies
		for item in self.items:
			marker = item.get_marker(MARKER_NAME)
			if marker is None:
				continue

			nodeid = clean_nodeid(item.nodeid)
			for dependency in marker.kwargs.get(MARKER_KWARG_DEPENDENCIES, []):
				# Make sure the name is absolute (ie file::[class::]method)
				if dependency not in self.name_to_items:
					dependency = get_absolute_nodeid(dependency, nodeid)

				# Add edge for the dependency
				for dependency_item in self.name_to_items[dependency]:
					dag.add_edge(dependency_item, item)

		# Return the sorted list
		return networkx.topological_sort(dag)
