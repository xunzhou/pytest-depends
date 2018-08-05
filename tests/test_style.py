import os.path
import subprocess


BASE_PATH = os.path.join(os.path.dirname(__file__), '..')


def test_pycodestyle(self):
	returncode = subprocess.call('pycodestyle', cwd = BASE_PATH)
	assert returncode == 0


def test_pydocstyle(self):
	returncode = subprocess.call('pydocstyle', cwd = BASE_PATH)
	assert returncode == 0
