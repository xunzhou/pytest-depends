"""
A module that provides the pytest hooks for this plugin.

The logic itself is in main.py.
"""

from pytest_depends.main import build_name_map
from pytest_depends.main import get_ordered_tests
from pytest_depends.main import print_name_map


def pytest_addoption(parser):  # noqa: D103
	group = parser.getgroup('depends')

	# Add an option to list all names + the tests they resolve to
	group.addoption(
		'--list-dependency-names',
		action = 'store_true',
		default = False,
		help = (
			'List all non-nodeid dependency names + the tests they resolve to. '
			'Will also list all nodeid dependency names when verbosity is high enough.'
		),
	)


def pytest_collection_modifyitems(session, config, items):  # noqa: D103
	# Build a mapping of names to matching tests
	session.name_to_items = build_name_map(items)

	# Show the dependency list if requested
	if config.getoption('list_dependency_names'):
		verbose = config.getoption('verbose') > 1
		print_name_map(session.name_to_items, verbose)

	# Reorder the items so that tests run after their dependencies
	items[:] = get_ordered_tests(session.name_to_items, items)
