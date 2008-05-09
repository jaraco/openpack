from sys import path
from os.path import join, abspath, dirname
path.insert(0, join(dirname(abspath(__file__)), '..'))
from openpack.basepack import Part

class SamplePart(Part):
	content_type = "text/pmxtest+xml"
	rel_type = "http://polimetrix.com/relationships/test"

