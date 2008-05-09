from setuptools import setup

setup(
    name="openpack",
    version="0.2",
    packages=['openpack'],
	package_data = {
		'openpack':['templates/*.tmpl'],
	}
)

