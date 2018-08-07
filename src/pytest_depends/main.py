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


class TestDependencies(object):
	""" Information about the resolved dependencies of a single test. """

	def __init__(self, item, manager):
		""" Create a new instance for a given test. """
		self.nodeid = clean_nodeid(item.nodeid)
		self.dependencies = set()

		marker = item.get_marker(MARKER_NAME)
		if marker is None:
			return

		for dependency in marker.kwargs.get(MARKER_KWARG_DEPENDENCIES, []):
			# If the name is not known, try to make it absolute (ie file::[class::]method)
			if dependency not in manager.name_to_nodeids:
				absolute_dependency = get_absolute_nodeid(dependency, self.nodeid)
				if absolute_dependency in manager.name_to_nodeids:
					dependency = absolute_dependency

			# Add all items matching the name
			for nodeid in manager.name_to_nodeids.get(dependency, []):
				self.dependencies.add(nodeid)


class DependencyManager(object):
	""" Keep track of tests, their names and their dependencies. """

	def __init__(self):
		"""
		Create a new DependencyManager.

		Should not be used directly, get_instance() instead.
		"""
		self._items = None
		self._name_to_nodeids = None
		self._nodeid_to_item = None
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

		self._name_to_nodeids = collections.defaultdict(list)
		self._nodeid_to_item = {}
		self._results = {}
		self._dependencies = {}

		for item in items:
			nodeid = clean_nodeid(item.nodeid)
			# Add the mapping from nodeid to the test item
			self._nodeid_to_item[nodeid] = item
			# Add the mappings from all names to the node id
			for name in get_names(item):
				self._name_to_nodeids[name].append(nodeid)
			# Create the object that will contain the results of this test
			self._results[nodeid] = TestResult(clean_nodeid(item.nodeid))

		# Don't allow using unknown keys on the name_to_nodeids mapping
		self._name_to_nodeids.default_factory = None

		for item in items:
			nodeid = clean_nodeid(item.nodeid)
			# Process the dependencies of this test
			# This uses the mappings created in the previous loop, and can thus not be merged into that loop
			self._dependencies[nodeid] = TestDependencies(item, self)

	@property
	def name_to_nodeids(self):  # noqa: D401
		""" A mapping from names to matching node id(s). """
		assert self.items is not None
		return self._name_to_nodeids

	@property
	def nodeid_to_item(self):  # noqa: D401
		""" A mapping from node ids to test items. """
		assert self.items is not None
		return self._nodeid_to_item

	@property
	def results(self):  # noqa: D401
		""" The results of the tests. """
		assert self.items is not None
		return self._results

	@property
	def dependencies(self):  # noqa: D401
		""" The dependencies of the tests. """
		assert self.items is not None
		return self._dependencies

	def print_name_map(self, verbose):
		""" Print a human-readable version of the name -> test mapping. """
		print('Dependency names:')
		for name, nodeids in sorted(self.name_to_nodeids.items(), key = lambda x: x[0]):
			if len(nodeids) == 1:
				if name == nodeids[0]:
					# This is just the base name, only print this when verbose
					if verbose:
						print('  {name}'.format(**locals()))
				else:
					# Name refers to a single node id, so use the short format
					print('  {name} -> {nodeids[0]}'.format(**locals()))
			else:
				# Name refers to multiple node ids, so use the long format
				print('  {name} ->'.format(**locals()))
				for nodeid in sorted(nodeids):
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
			nodeid = clean_nodeid(item.nodeid)
			for dependency in self.dependencies[nodeid].dependencies:
				dag.add_edge(self.nodeid_to_item[dependency], item)

		# Return the sorted list
		return networkx.topological_sort(dag)

	def register_result(self, item, result):
		""" Register a result of a test. """
		nodeid = clean_nodeid(item.nodeid)
		self.results[nodeid].register_result(result)

	def get_blockers(self, item):
		""" Get a list of unfulfilled dependencies for a test. """
		nodeid = clean_nodeid(item.nodeid)
		blockers = []
		for dependency in self.dependencies[nodeid].dependencies:
			result = self.results[dependency]
			if not result.success:
				blockers.append(dependency)
		return blockers
