from setuptools import setup

setup(
	name="openpack",
	author="Christian Wyglendowski (YouGov), Jason R. Coombs (YouGov)",
	use_hg_version=True,
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
	setup_requires = [
		'hgtools >= 0.4.7',
	],
)
