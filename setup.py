from setuptools import setup

setup(
	name="openpack",
	author="Christian Wyglendowski (YouGov)",
	version="0.4-dev",
	packages=['openpack'],
	install_requires=[
		'lxml',
	],
	tests_require=[
		'py.test>=1.0',
	],
)
