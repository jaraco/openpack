import os

with open(os.path.join(os.path.dirname(__file__), 'README')) as f:
	long_description = f.read()

setup_params = dict(
	name="openpack",
	author="Christian Wyglendowski (YouGov), Jason R. Coombs (YouGov)",
	author_email="open.source@yougov.com",
	url="https://bitbucket.org/yougov/openpack",
	use_hg_version=True,
	long_description=long_description,
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
		'hgtools>=1.0',
	],
)

if __name__ == '__main__':
	from setuptools import setup
	setup(**setup_params)
