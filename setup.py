from setuptools import setup

setup(
	name="openpack",
	author="Christian Wyglendowski (YouGov), Jason R. Coombs (YouGov)",
	version="0.4.2-dev",
	long_description=open("README").read(),
	packages=['openpack'],
	install_requires=[
		'lxml',
	],
	tests_require=[
		'py.test>=1.0',
	],
	entry_points = {
		'console_scripts': [
			'part-edit = openpack.editor:part_edit_cmd',
			'zip-listdir = openpack.editor:pack_dir_cmd',
			],
	},
)
