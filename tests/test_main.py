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
		result = testdir.runpytest_subprocess('-v')
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
			@pytest.mark.parametrize('num', [1, 2])
			def test_bar(num):
				pass
		""")
		result = testdir.runpytest_subprocess('-v')
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
		result = testdir.runpytest_subprocess('-v')
		result.stdout.fnmatch_lines([
			'*::test_bar PASSED*',
			'*::test_foo PASSED*',
		])
		assert result.ret == 0


class TestDependencySkip(object):
	def test_fail(self, testdir):
		testdir.makepyfile("""
			import pytest
			def test_bar():
				assert 1 == 2
			@pytest.mark.depends(on=['test_bar'])
			def test_foo():
				pass
		""")
		result = testdir.runpytest_subprocess('-v')
		result.stdout.fnmatch_lines_random([
			'*::test_bar FAILED*',
			'*::test_foo SKIPPED*',
		])
		assert result.ret != 0

	def test_setup_fail(self, testdir):
		testdir.makepyfile("""
			import pytest
			@pytest.fixture
			def broken_setup():
				raise Exception('This is broken')
			def test_bar(broken_setup):
				pass
			@pytest.mark.depends(on=['test_bar'])
			def test_foo():
				pass
		""")
		result = testdir.runpytest_subprocess('-v')
		result.stdout.fnmatch_lines_random([
			'*::test_bar ERROR*',
			'*::test_foo SKIPPED*',
		])
		assert result.ret != 0

	def test_teardown_fail(self, testdir):
		testdir.makepyfile("""
			import pytest
			@pytest.fixture
			def broken_teardown():
				yield
				raise Exception('This is broken')
			def test_bar(broken_teardown):
				pass
			@pytest.mark.depends(on=['test_bar'])
			def test_foo():
				pass
		""")
		result = testdir.runpytest_subprocess('-v')
		result.stdout.fnmatch_lines_random([
			'*::test_bar ERROR*',
			'*::test_foo SKIPPED*',
		])
		assert result.ret != 0

	def test_skip(self, testdir):
		testdir.makepyfile("""
			import pytest
			@pytest.mark.skip
			def test_bar():
				pass
			@pytest.mark.depends(on=['test_bar'])
			def test_foo():
				pass
		""")
		result = testdir.runpytest_subprocess('-v')
		result.stdout.fnmatch_lines_random([
			'*::test_bar SKIPPED*',
			'*::test_foo SKIPPED*',
		])
		assert result.ret == 0

	def test_parametrized_fail(self, testdir):
		testdir.makepyfile("""
			import pytest
			@pytest.mark.parametrize('num', [1, 2])
			def test_bar(num):
				assert num == 1
			@pytest.mark.depends(on=['test_bar'])
			def test_foo():
				pass
		""")
		result = testdir.runpytest_subprocess('-v')
		result.stdout.fnmatch_lines_random([
			'*::test_bar* PASSED*',
			'*::test_bar* FAILED*',
			'*::test_foo SKIPPED*',
		])
		assert result.ret != 0

	def test_missing_run(self, testdir):
		testdir.makepyfile("""
			import pytest
			@pytest.mark.depends(on=['baz'])
			def test_foo():
				pass
		""")
		result = testdir.runpytest_subprocess('-v', '--missing-dependency-action=run')
		result.stdout.fnmatch_lines_random([
			'*::test_foo PASSED*',
		])
		assert result.ret == 0

	def test_missing_skip(self, testdir):
		testdir.makepyfile("""
			import pytest
			@pytest.mark.depends(on=['baz'])
			def test_foo():
				pass
		""")
		result = testdir.runpytest_subprocess('-v', '--missing-dependency-action=skip')
		result.stdout.fnmatch_lines_random([
			'*::test_foo SKIPPED*',
		])
		assert result.ret == 0

	def test_missing_fail(self, testdir):
		testdir.makepyfile("""
			import pytest
			@pytest.mark.depends(on=['baz'])
			def test_foo():
				pass
		""")
		result = testdir.runpytest_subprocess('-v', '--missing-dependency-action=fail')
		result.stdout.fnmatch_lines_random([
			'*::test_foo FAILED*',
		])
		assert result.ret == 1


class TestListDependencyNames(object):
	def test_scope_single(self, testdir):
		testdir.makepyfile("""
			def test_foo():
				pass
		""")
		result = testdir.runpytest_subprocess('--list-dependency-names')
		result.stdout.fnmatch_lines([
			'Available dependency names:',
			'*.py -> *::test_foo',
			'collected *',
		])
		assert result.ret == 0

	def test_scope_multi(self, testdir):
		testdir.makepyfile("""
			def test_foo():
				pass
			def test_bar():
				pass
		""")
		result = testdir.runpytest_subprocess('--list-dependency-names')
		result.stdout.fnmatch_lines([
			'Available dependency names:',
			'*.py ->',
			'  *::test_bar',
			'  *::test_foo',
			'collected *',
		])
		assert result.ret == 0

	def test_alias(self, testdir):
		testdir.makepyfile("""
			import pytest
			@pytest.mark.depends(name = 'baz')
			def test_foo():
				pass
		""")
		result = testdir.runpytest_subprocess('--list-dependency-names')
		result.stdout.fnmatch_lines([
			'Available dependency names:',
			'*baz -> *::test_foo',
			'collected *',
		])
		assert result.ret == 0

	def test_multi_target_alias(self, testdir):
		testdir.makepyfile("""
			import pytest
			@pytest.mark.depends(name = 'baz')
			def test_foo():
				pass
			@pytest.mark.depends(name = 'baz')
			def test_bar():
				pass
		""")
		result = testdir.runpytest_subprocess('--list-dependency-names')
		result.stdout.fnmatch_lines([
			'Available dependency names:',
			'*baz ->',
			'  *::test_bar',
			'  *::test_foo',
			'collected *',
		])
		assert result.ret == 0


class TestListProcessedDependencies(object):
	def test_simple(self, testdir):
		testdir.makepyfile("""
			import pytest
			@pytest.mark.depends(on=['test_bar'])
			def test_foo():
				pass
			def test_bar():
				pass
		""")
		result = testdir.runpytest_subprocess('--list-processed-dependencies')
		result.stdout.fnmatch_lines([
			'Dependencies:',
			'*::test_foo*',
			'  *::test_bar',
			'collected *',
		])
		assert result.ret == 0

	def test_parametrized(self, testdir):
		testdir.makepyfile("""
			import pytest
			@pytest.mark.depends(on=['test_bar'])
			def test_foo():
				pass
			@pytest.mark.parametrize('num', [1, 2])
			def test_bar(num):
				pass
		""")
		result = testdir.runpytest_subprocess('--list-processed-dependencies')
		result.stdout.fnmatch_lines([
			'Dependencies:',
			'*::test_foo*',
			'  *::test_bar*',
			'  *::test_bar*',
			'collected *',
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
		result = testdir.runpytest_subprocess('--list-processed-dependencies')
		result.stdout.fnmatch_lines([
			'Dependencies:',
			'*::test_foo*',
			'  *::test_bar',
			'collected *',
		])
		assert result.ret == 0

	def test_missing(self, testdir):
		testdir.makepyfile("""
			import pytest
			@pytest.mark.depends(on=['baz'])
			def test_foo():
				pass
		""")
		result = testdir.runpytest_subprocess('--list-processed-dependencies')
		result.stdout.fnmatch_lines([
			'Dependencies:',
			'*::test_foo*',
			'  *baz (MISSING)',
			'collected *',
		])
		assert result.ret == 0
