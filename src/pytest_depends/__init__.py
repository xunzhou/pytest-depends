"""
A module that provides the pytest hooks for this plugin.

The logic itself is in main.py.
"""

from pytest_depends.main import build_name_map
from pytest_depends.main import get_ordered_tests


def pytest_collection_modifyitems(session, items):  # noqa: D103
	# Build a mapping of names to matching tests
	session.name_to_items = build_name_map(items)

	# Reorder the items so that tests run after their dependencies
	items[:] = get_ordered_tests(session.name_to_items, items)
