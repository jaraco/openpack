try:
	from cStringIO import StringIO
except ImportError:
	from StringIO import StringIO
import os

import py.test

from openpack.basepack import *
from openpack.zippack import ZipPackage

from common import SamplePart

TESTFILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'temp.zipx')

class TestZipPack(object):
	def setup_method(self, method):
		self.remove_testfile()

	def test_create(self):
		self.pack = ZipPackage(TESTFILE)
	
	def test_add_part(self):
		self.test_create()
		self.part = p = SamplePart(self.pack, '/test/part.xml')
		self.pack[p.name] = p
		self.pack.content_types.add_override(p)
		self.pack.relate(p)
	
	def test_write_to_part(self):
		self.test_add_part()
		self.part.data = '<test>hi there</test>'
	
	def test_save(self):
		self.test_write_to_part()
		self.pack.save()
		del self.pack
		del self.part
	
	def test_open(self):
		self.test_save()
		self.pack = ZipPackage(TESTFILE)
	
	def test_contents(self):
		self.test_open()
		assert '/test/part.xml' in self.pack
		self.part = self.pack['/test/part.xml']
		assert self.part.data == '<test>hi there</test>'
	
	def test_relationships(self):
		self.test_contents()
		print self.pack.relationships.children
		assert self.pack.related('http://polimetrix.com/relationships/test')[0] == self.part

	def teardown_method(self, method):
		if hasattr(self, 'pack'): del self.pack
		if hasattr(self, 'part'): del self.part
		self.remove_testfile()

	@staticmethod
	def remove_testfile():
		if os.path.exists(TESTFILE):
			os.remove(TESTFILE)

