"""uses_*: Provides a set of fixtures used to mark tests for filtering on the command-line.

Tests using these fixtures directly or indirectly can be filtered using py.test's
``-k`` filter argument. For example, run tests that use the ssh client::

    py.test -k uses_ssh

Additionally, tests using one of the fixtures listed in :py:attr:`appliance_marks` will be marked
with `is_appliance`, for easily filtering out appliance tests, e.g::

    py.test -k 'not is_appliance'

All fixtures created by this module will have the ``uses_`` prefix.

Note:
    ``is_appliance`` is a mark that will be dynamically set based on fixtures used,
    but is not a fixture itself.

"""
import pytest

# List of fixture marks to create and use for test marking
# these are exposed as globals and individually documented
USES_FIXTURENAMES = set()

##
# Create the fixtures that will trigger test marking
##


def _markfixture(func):
    if func.__doc__ is None:
        func.__doc__ = "Fixture which marks a test with the ``{}`` mark".format(func.__name__)
    USES_FIXTURENAMES.add(func.__name__)
    return pytest.fixture(scope="session")(func)


@_markfixture
def uses_event_listener():
    pass


@_markfixture
def uses_pxe():
    pass


@_markfixture
def uses_providers():
    pass


@_markfixture
def is_appliance():
    pass


@_markfixture
def uses_db(is_appliance):
    """fixture that marks tests with a ``uses_db`` and a ``is_appliance`` mark"""


@_markfixture
def uses_ssh(is_appliance):
    """fixture that marks tests with a ``uses_ssh`` and a ``is_appliance`` mark"""


@_markfixture
def uses_cloud_providers(uses_providers):
    """Fixture which marks a test with the ``uses_cloud_providers`` and ``uses_providers`` marks"""
    pass


@_markfixture
def uses_infra_providers(uses_providers):
    """Fixture which marks a test with the ``uses_infra_providers`` and ``uses_providers`` marks"""
    pass


###
# Now hook the item collector to apply all the correct marks
###
def pytest_itemcollected(item):
    """pytest hook that actually does the marking

    See: http://pytest.org/latest/plugins.html#_pytest.hookspec.pytest_collection_modifyitems

    """
    try:
        # Intersect 'uses_' fixture set with the fixtures being used by a test
        mark_fixtures = USES_FIXTURENAMES.intersection(item.fixturenames)
    except AttributeError:
        # Test doesn't have fixturenames, make no changes
        return

    for name in mark_fixtures:
        item.add_marker(name)
        item.extra_keyword_matches.add(name)
