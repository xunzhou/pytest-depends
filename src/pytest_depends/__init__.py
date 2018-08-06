"""
A module that provides the pytest hooks for this plugin.

The logic itself is in main.py.
"""

from pytest_depends.main import DependencyManager


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


def pytest_collection_modifyitems(config, items):  # noqa: D103
	manager = DependencyManager.get_instance()

	# Register the founds tests on the manager
	manager.items = items

	# Show the dependency list if requested
	if config.getoption('list_dependency_names'):
		verbose = config.getoption('verbose') > 1
		manager.print_name_map(verbose)

	# Reorder the items so that tests run after their dependencies
	items[:] = manager.sorted_items
