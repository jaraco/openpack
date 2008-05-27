try:
	from cStringIO import StringIO
except ImportError:
	from StringIO import StringIO
import os

import py.test

from common import SamplePart
from openpack.basepack import *
from openpack.zippack import ZipPackage

TESTFILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'temp.zipx')

class TestZipPack(object):
	def test_create(self):
		self.pack = ZipPackage(TESTFILE)
	
	def test_add_part(self):
		self.part = p = SamplePart(self.pack, '/test/part.xml')
		self.pack[p.name] = p
		self.pack.content_types.add_override(p)
		self.pack.relate(p)
	
	def test_write_to_part(self):
		self.part.data = '<test>hi there</test>'
	
	def test_save(self):
		self.pack.save()
		del self.pack
		del self.part
	
	def test_open(self):
		self.pack = ZipPackage(TESTFILE)
	
	def test_contents(self):
		assert '/test/part.xml' in self.pack
		self.part = self.pack['/test/part.xml']
		assert self.part.data == '<test>hi there</test>'
	
	def test_relationships(self):
		print self.pack.relationships.children
		assert self.pack.related('http://polimetrix.com/relationships/test')[0] == self.part

	def teardown_class(cls):
		os.remove(TESTFILE)

