import py.test

from openpack.basepack import Package, Part


class TestParts(object):
	def setup_class(cls):
		cls.package = Package()

	def test_create(self):
		self.part = Part(self.package, '/something.html', 'text/html')

	def test_bad_names(self):
		py.test.raises(ValueError, Part, self.package, 'something', 'text/html')
