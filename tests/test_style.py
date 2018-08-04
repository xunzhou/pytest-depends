import os.path
import subprocess


BASE_PATH = os.path.join(os.path.dirname(__file__), '..')


class TestPycodestyle(object):
	def test(self):
		returncode = subprocess.call('pycodestyle', cwd = BASE_PATH)
		assert returncode == 0


class TestPydocstyle(object):
	def test(self):
		returncode = subprocess.call('pydocstyle', cwd = BASE_PATH)
		assert returncode == 0
