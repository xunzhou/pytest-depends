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


def build_name_map(items):
	""" Build a map from name to test(s). """
	mapping = collections.defaultdict(list)
	for item in items:
		names = get_names(item)
		for name in names:
			mapping[name].append(item)
	return mapping


def print_name_map(mapping, verbose):
	""" Print a human-readable version of the name -> item mapping. """
	print('Dependency names:')
	for name, name_items in sorted(mapping.items(), key = lambda x: x[0]):
		if len(name_items) == 1:
			nodeid = clean_nodeid(name_items[0].nodeid)
			if name == nodeid:
				# This is just the base name, only print this when verbose
				if verbose:
					print(f'  {name}')
			else:
				# Name refers to a single node id, so use the short format
				print(f'  {name} -> {nodeid}')
		else:
			# Name refers to multiple node ids, so use the long format
			print(f'  {name} ->')
			nodeids = [clean_nodeid(item.nodeid) for item in name_items]
			nodeids.sort()
			for nodeid in nodeids:
				print(f'    {nodeid}')


def get_ordered_tests(mapping, items):
	""" Get a sorted list of tests where all tests are sorted after their dependencies. """
	# Build a directed graph for sorting
	dag = networkx.DiGraph()

	# Insert all items as nodes, to prevent items that have no dependencies and are not dependencies themselves from
	# being lost
	dag.add_nodes_from(items)

	# Insert edges for all the dependencies
	for item in items:
		marker = item.get_marker(MARKER_NAME)
		if marker is None:
			continue

		nodeid = clean_nodeid(item.nodeid)
		for dependency in marker.kwargs.get(MARKER_KWARG_DEPENDENCIES, []):
			# Make sure the name is absolute (ie file::[class::]method)
			if dependency not in mapping:
				dependency = get_absolute_nodeid(dependency, nodeid)

			# Add edge for the dependency
			for dependency_item in mapping[dependency]:
				dag.add_edge(dependency_item, item)

	# Return the sorted list
	return networkx.topological_sort(dag)