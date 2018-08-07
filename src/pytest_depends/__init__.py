"""
A module that provides the pytest hooks for this plugin.

The logic itself is in main.py.
"""

import pytest

from pytest_depends.main import DependencyManager
from pytest_depends.util import clean_nodeid


MISSING_DEPENDENCY_ACTIONS = {
	'run': None,
	'skip': lambda m: pytest.skip(m),
	'fail': lambda m: pytest.fail(m, False),
}


def pytest_addoption(parser):  # noqa: D103
	group = parser.getgroup('depends')

	# Add a flag to list all names + the tests they resolve to
	group.addoption(
		'--list-dependency-names',
		action = 'store_true',
		default = False,
		help = (
			'List all non-nodeid dependency names + the tests they resolve to. '
			'Will also list all nodeid dependency names when verbosity is high enough.'
		),
	)

	# Add a flag to list all (resolved) dependencies for all tests + unresolvable names
	group.addoption(
		'--list-processed-dependencies',
		action = 'store_true',
		default = False,
		help = 'List all dependencies of all tests as a list of nodeids + the names that could not be resolved.',
	)

	# Add an ini option + flag to choose the action to take for unresolved dependencies
	help_message = (
		'The action to take when a test has dependencies that cannot be found within the current scope. '
		'Use "run" to run the test anyway, "skip" to skip the test, and "fail" to fail the test.'
	)
	parser.addini('missing_dependency_action', help_message, default = 'skip')
	group.addoption(
		'--missing-dependency-action',
		choices = MISSING_DEPENDENCY_ACTIONS.keys(),
		default = None,
		help = help_message,
	)


def pytest_configure(config):  # noqa: D103
	manager = DependencyManager.get_instance()

	# Setup the handling of unresolved dependencies
	missing_dependency_action = config.getini('missing_dependency_action')
	if missing_dependency_action is not None and missing_dependency_action not in MISSING_DEPENDENCY_ACTIONS:
		choices = ', '.join(MISSING_DEPENDENCY_ACTIONS.keys())
		raise Exception('Invalid ini value for missing_dependency_action, choose from {choices}'.format(**locals()))
	missing_dependency_action = config.getoption('missing_dependency_action') or missing_dependency_action
	manager.options['missing_dependency_action'] = MISSING_DEPENDENCY_ACTIONS[missing_dependency_action]


def pytest_collection_modifyitems(config, items):  # noqa: D103
	manager = DependencyManager.get_instance()

	# Register the founds tests on the manager
	manager.items = items

	# Show the extra information if requested
	if config.getoption('list_dependency_names'):
		verbose = config.getoption('verbose') > 1
		manager.print_name_map(verbose)
	if config.getoption('list_processed_dependencies'):
		color = config.getoption('color')
		manager.print_processed_dependencies(color)

	# Reorder the items so that tests run after their dependencies
	items[:] = manager.sorted_items


@pytest.hookimpl(tryfirst = True, hookwrapper = True)
def pytest_runtest_makereport(item, call):  # noqa: D103
	manager = DependencyManager.get_instance()

	# Run the step
	outcome = yield

	# Store the result on the manager
	manager.register_result(item, outcome.result)


def pytest_runtest_call(item):  # noqa: D103
	manager = DependencyManager.get_instance()

	# Handle missing dependencies
	missing_dependency_action = manager.options['missing_dependency_action']
	missing = manager.get_missing(item)
	if missing_dependency_action and missing:
		missing_text = ', '.join(missing)
		missing_dependency_action('{item.nodeid} depends on {missing_text}, which was not found'.format(**locals()))

	# Check whether all dependencies succeeded
	blockers = manager.get_blockers(item)
	if blockers:
		blocking_text = ', '.join(blockers)
		pytest.skip('{item.nodeid} depends on {blocking_text}'.format(**locals()))
