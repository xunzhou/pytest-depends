class TestOrder(object):
	def test_simple(self, testdir):
		testdir.makepyfile("""
			import pytest
			@pytest.mark.depends(on=['test_bar'])
			def test_foo():
				pass
			def test_bar():
				pass
		""")
		result = testdir.runpytest('-v')
		result.stdout.fnmatch_lines([
			'*::test_bar PASSED*',
			'*::test_foo PASSED*',
		])
		assert result.ret == 0

	def test_parametrized(self, testdir):
		testdir.makepyfile("""
			import pytest
			@pytest.mark.depends(on=['test_bar'])
			def test_foo():
				pass
			@pytest.mark.parametrize('num', [[1], [2]])
			def test_bar(num):
				pass
		""")
		result = testdir.runpytest('-v')
		result.stdout.fnmatch_lines([
			'*::test_bar* PASSED*',
			'*::test_bar* PASSED*',
			'*::test_foo PASSED*',
		])
		assert result.ret == 0

	def test_name(self, testdir):
		testdir.makepyfile("""
			import pytest
			@pytest.mark.depends(on=['baz'])
			def test_foo():
				pass
			@pytest.mark.depends(name='baz')
			def test_bar():
				pass
		""")
		result = testdir.runpytest('-v')
		result.stdout.fnmatch_lines([
			'*::test_bar PASSED*',
			'*::test_foo PASSED*',
		])
		assert result.ret == 0
