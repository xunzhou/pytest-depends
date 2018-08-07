# -*- coding: future_fstrings -*-

""" Utility functions to process the identifiers of tests. """

import re

from pytest_depends.constants import MARKER_NAME
from pytest_depends.constants import MARKER_KWARG_ID


REGEX_PARAMETERS = re.compile(r'\[.+\]$')


def clean_nodeid(nodeid):
	"""
	Remove any superfluous ::() from a node id.

	>>> clean_nodeid('test_file.py::TestClass::()::test')
	'test_file.py::TestClass::test'
	>>> clean_nodeid('test_file.py::TestClass::test')
	'test_file.py::TestClass::test'
	>>> clean_nodeid('test_file.py::test')
	'test_file.py::test'
	"""
	return nodeid.replace('::()::', '::')


def strip_nodeid_parameters(nodeid):
	"""
	Strip parameters from a node id.

	>>> strip_nodeid_parameters('test_file.py::TestClass::test[foo]')
	'test_file.py::TestClass::test'
	>>> strip_nodeid_parameters('test_file.py::TestClass::test')
	'test_file.py::TestClass::test'
	"""
	return REGEX_PARAMETERS.sub('', nodeid)


def get_absolute_nodeid(nodeid, scope):
	"""
	Transform a possibly relative node id to an absolute one using the scope in which it is used.

	>>> scope = 'test_file.py::TestClass::test'
	>>> get_absolute_nodeid('test2', scope)
	'test_file.py::TestClass::test2'
	>>> get_absolute_nodeid('TestClass2::test2', scope)
	'test_file.py::TestClass2::test2'
	>>> get_absolute_nodeid('test_file2.py::TestClass2::test2', scope)
	'test_file2.py::TestClass2::test2'
	"""
	parts = nodeid.split('::')
	# Completely relative (test_name), so add the full current scope (either file::class or file)
	if len(parts) == 1:
		base_nodeid = scope.rsplit('::', 1)[0]
		nodeid = f'{base_nodeid}::{nodeid}'
	# Contains some scope already (Class::test_name), so only add the current file scope
	elif '.' not in parts[0]:
		base_nodeid = scope.split('::', 1)[0]
		nodeid = f'{base_nodeid}::{nodeid}'
	return clean_nodeid(nodeid)


def get_names(item):
	"""
	Get all names for a test.

	This will use the following methods to determine the name of the test:
		- If given, the custom name(s) passed to the keyword argument name on the marker
		- The full node id of the test
		- The node id of the test with any parameters removed, if it had any
		- All 'scope' parts of the node id. For example, for a test test_file.py::TestClass::test, this would be
		test_file.py and test_file.py::TestClass
	"""
	names = set()

	# Node id
	nodeid = clean_nodeid(item.nodeid)
	names.add(nodeid)

	# Node id without parameter
	nodeid = strip_nodeid_parameters(nodeid)
	names.add(nodeid)

	# Node id scopes
	while '::' in nodeid:
		nodeid = nodeid.rsplit('::', 1)[0]
		names.add(nodeid)

	# Custom name
	marker = item.get_marker(MARKER_NAME)
	if marker and MARKER_KWARG_ID in marker.kwargs:
		names.add(marker.kwargs[MARKER_KWARG_ID])

	return names
