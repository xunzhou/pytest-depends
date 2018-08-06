import pytest_depends.util as testmodule


class TestCleanNodeid(object):
	def test_full_id(self):
		assert testmodule.clean_nodeid('test_file.py::TestClass::()::test') == 'test_file.py::TestClass::test'

	def test_already_cleaned(self):
		assert testmodule.clean_nodeid('test_file.py::TestClass::test') == 'test_file.py::TestClass::test'

	def test_no_class(self):
		assert testmodule.clean_nodeid('test_file.py::test') == 'test_file.py::test'


class TestStripNodeidParameters(object):
	def test_single_parameter(self):
		assert testmodule.strip_nodeid_parameters('test_file.py::TestClass::test[foo]') == 'test_file.py::TestClass::test'

	def test_no_parameter(self):
		assert testmodule.strip_nodeid_parameters('test_file.py::TestClass::test') == 'test_file.py::TestClass::test'


class TestGetAbsoluteNodeid(object):
	def test_relative_from_class(self):
		scope = 'test_file.py::TestClass::test'
		assert testmodule.get_absolute_nodeid('test2', scope) == 'test_file.py::TestClass::test2'

	def test_relative_from_file(self):
		scope = 'test_file.py::test'
		assert testmodule.get_absolute_nodeid('test2', scope) == 'test_file.py::test2'

	def test_relative_class_from_class(self):
		scope = 'test_file.py::TestClass::test'
		assert testmodule.get_absolute_nodeid('TestClass2::test2', scope) == 'test_file.py::TestClass2::test2'

	def test_relative_class_from_file(self):
		scope = 'test_file.py::test'
		assert testmodule.get_absolute_nodeid('TestClass2::test2', scope) == 'test_file.py::TestClass2::test2'

	def test_absolute_from_class(self):
		scope = 'test_file.py::TestClass::test'
		actual = testmodule.get_absolute_nodeid('test_file2.py::test2', scope)
		assert actual == 'test_file2.py::test2'

	def test_absolute_from_file(self):
		scope = 'test_file.py::test'
		actual = testmodule.get_absolute_nodeid('test_file2.py::test2', scope)
		assert actual == 'test_file2.py::test2'

	def test_absolute_class_from_class(self):
		scope = 'test_file.py::TestClass::test'
		actual = testmodule.get_absolute_nodeid('test_file2.py::TestClass2::test2', scope)
		assert actual == 'test_file2.py::TestClass2::test2'

	def test_absolute_class_from_file(self):
		scope = 'test_file.py::test'
		actual = testmodule.get_absolute_nodeid('test_file2.py::TestClass2::test2', scope)
		assert actual == 'test_file2.py::TestClass2::test2'
