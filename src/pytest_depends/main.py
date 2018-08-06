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


class TestResult(object):
	""" Keeps track of the results of a single test. """

	STEPS = ['setup', 'call', 'teardown']
	GOOD_OUTCOMES = ['passed']

	def __init__(self, nodeid):
		""" Create a new instance for a test with a given node id. """
		self.nodeid = nodeid
		self.results = {}

	def register_result(self, result):
		""" Register a result of this test. """
		if result.when not in self.STEPS:
			raise Exception('Received result for unknown step {result.when} of test {self.nodeid}'.format(**locals()))
		if result.when in self.results:
			raise Exception('Received multiple results for step {result.when} of test {self.nodeid}'.format(**locals()))
		self.results[result.when] = result.outcome

	@property
	def success(self):
		""" Whether the entire test was successful. """
		print(self.nodeid, self.results)
		for step in self.STEPS:
			if step not in self.results or self.results[step] not in self.GOOD_OUTCOMES:
				return False
		return True


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

		# Create results for each of the tests
		self._results = {}
		for item in items:
			self._results[item] = TestResult(clean_nodeid(item.nodeid))

	@property
	def name_to_items(self):  # noqa: D401
		""" A mapping from names to test(s). """
		assert self.items is not None
		return self._name_to_items

	@property
	def results(self):  # noqa: D401
		""" The results of the tests. """
		assert self.items is not None
		return self._results

	def _get_dependencies(self, item):
		""" Get the dependencies of a test as a list of test functions. """
		marker = item.get_marker(MARKER_NAME)
		if marker is None:
			return []

		nodeid = clean_nodeid(item.nodeid)
		dependencies = set()
		for dependency_name in marker.kwargs.get(MARKER_KWARG_DEPENDENCIES, []):
			# If the name is not known, try to make it absolute (ie file::[class::]method)
			if dependency_name not in self.name_to_items:
				absolute_dependency_name = get_absolute_nodeid(dependency_name, nodeid)
				if absolute_dependency_name in self.name_to_items:
					dependency_name = absolute_dependency_name

			# Add all items matching the name
			for dependency_item in self.name_to_items[dependency_name]:
				dependencies.add(dependency_item)
		return dependencies

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
			for dependency in self._get_dependencies(item):
				dag.add_edge(dependency, item)

		# Return the sorted list
		return networkx.topological_sort(dag)

	def register_result(self, item, result):
		""" Register a result of a test. """
		self.results[item].register_result(result)

	def get_blockers(self, item):
		""" Get a list of unfulfilled dependencies for a test. """
		blockers = []
		for dependency in self._get_dependencies(item):
			result = self.results[dependency]
			if not result.success:
				blockers.append(dependency)
		return blockers
