# -*- coding: future_fstrings -*-

"""
A module that provides the pytest hooks for this plugin.

The logic itself is in main.py.
"""

import pytest

from pytest_depends.main import DependencyManager
from pytest_depends.util import clean_nodeid


# Each test suite run should have a single manager object. For regular runs, a simple singleton would suffice, but for
# our own tests this causes problems, as the nested pytest runs get the same instance. This can be worked around by
# running them all in subprocesses, but this slows the tests down massively. Instead, keep a stack of managers, so each
# test suite will have its own manager, even nested ones.
managers = []


DEPENDENCY_PROBLEM_ACTIONS = {
	'run': None,
	'skip': lambda m: pytest.skip(m),
	'fail': lambda m: pytest.fail(m, False),
}


def _add_ini_and_option(parser, group, name, help, default, **kwargs):
	""" Add an option to both the ini file as well as the command line flags, with the latter overriding the former. """
	parser.addini(name, help + ' This overrides the similarly named option from the config.', default = default)
	group.addoption(f'--{name.replace("_", "-")}', help = help, default = None, **kwargs)


def _get_ini_or_option(config, name, choices):
	""" Get an option from either the ini file or the command line flags, the latter taking precedence. """
	value = config.getini(name)
	if value is not None and choices is not None and value not in choices:
		raise Exception(f'Invalid ini value for {name}, choose from {", ".join(choices)}')
	return config.getoption(name) or value


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

	# Add an ini option + flag to choose the action to take for failed dependencies
	_add_ini_and_option(
		parser,
		group,
		name = 'failed_dependency_action',
		help = (
			'The action to take when a test has dependencies that failed. '
			'Use "run" to run the test anyway, "skip" to skip the test, and "fail" to fail the test.'
		),
		default = 'skip',
		choices = DEPENDENCY_PROBLEM_ACTIONS.keys(),
	)

	# Add an ini option + flag to choose the action to take for unresolved dependencies
	_add_ini_and_option(
		parser,
		group,
		name = 'missing_dependency_action',
		help = (
			'The action to take when a test has dependencies that cannot be found within the current scope. '
			'Use "run" to run the test anyway, "skip" to skip the test, and "fail" to fail the test.'
		),
		default = 'skip',
		choices = DEPENDENCY_PROBLEM_ACTIONS.keys(),
	)


def pytest_configure(config):  # noqa: D103
	manager = DependencyManager()
	managers.append(manager)

	# Setup the handling of problems with dependencies
	manager.options['failed_dependency_action'] = _get_ini_or_option(
		config,
		'failed_dependency_action',
		DEPENDENCY_PROBLEM_ACTIONS.keys(),
	)
	manager.options['missing_dependency_action'] = _get_ini_or_option(
		config,
		'missing_dependency_action',
		DEPENDENCY_PROBLEM_ACTIONS.keys(),
	)


def pytest_collection_modifyitems(config, items):  # noqa: D103
	manager = managers[-1]

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
	manager = managers[-1]

	# Run the step
	outcome = yield

	# Store the result on the manager
	manager.register_result(item, outcome.result)


def pytest_runtest_call(item):  # noqa: D103
	manager = managers[-1]

	# Handle missing dependencies
	missing_dependency_action = DEPENDENCY_PROBLEM_ACTIONS[manager.options['missing_dependency_action']]
	missing = manager.get_missing(item)
	if missing_dependency_action and missing:
		missing_dependency_action(f'{item.nodeid} depends on {", ".join(missing)}, which was not found')

	# Check whether all dependencies succeeded
	failed_dependency_action = DEPENDENCY_PROBLEM_ACTIONS[manager.options['failed_dependency_action']]
	failed = manager.get_failed(item)
	if failed_dependency_action and failed:
		failed_dependency_action(f'{item.nodeid} depends on {", ".join(failed)}')


def pytest_unconfigure():  # noqa: D103
	managers.pop()
