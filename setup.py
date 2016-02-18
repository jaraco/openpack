import os

with open(os.path.join(os.path.dirname(__file__), 'README')) as f:
	long_description = f.read()

setup_params = dict(
	name="openpack",
	author="Christian Wyglendowski (YouGov), Jason R. Coombs (YouGov)",
	author_email="open.source@yougov.com",
	url="https://bitbucket.org/yougov/openpack",
	use_scm_version=True,
	long_description=long_description,
	packages=['openpack'],
	license = 'MIT',
	classifiers = [
		"Development Status :: 5 - Production/Stable",
		"Intended Audience :: Developers",
		"Programming Language :: Python :: 2.6",
		"Programming Language :: Python :: 2.7",
		"Programming Language :: Python :: 3",
	],
	entry_points = {
		'console_scripts': [
			'part-edit = openpack.editor:part_edit_cmd',
			'zip-listdir = openpack.editor:pack_dir_cmd',
			],
	},
	install_requires=[
		'lxml',
		'six',
		'jaraco.collections>=1.3.2',
	],
	tests_require=[
		'pytest',
	],
	setup_requires = [
		'setuptools_scm',
		'pytest-runner',
	],
)

if __name__ == '__main__':
	from setuptools import setup
	setup(**setup_params)
