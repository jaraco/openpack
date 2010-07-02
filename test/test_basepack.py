import py.test
import re

from common import SamplePart
from openpack.basepack import *

class TestBasicPart(object):
	def test_good_names(self):
		for n in ('/abc', '/foo/bar', '/foo-1/bar.xml'):
			yield self.check_name, n
	
	def check_name(self, name, should_fail=False):
		if should_fail:
			py.test.raises(ValueError, Part, None, name)
		else:
			p = Part(None, name)
	
	def test_bad_names(self):
		for n in ('abc', '/abc/', '/foo/bar.', '/bar/./abc.xml'):
			yield self.check_name, n, True

	def test_part_rels(self):
		p = Part(None, '/word/document.xml')
		assert isinstance(p.relationships, Relationships)

class TestBasicPackage(object):
	def test_create(self):
		self.pack = Package()

	def test_package_rels(self):
		self.test_create()
		assert self.pack.relationships
		assert self.pack['/_rels/.rels']
		assert self.pack.relationships == self.pack['/_rels/.rels']

	def test_content_types(self):
		self.test_package_rels()
		# the content types part is not addressable
		assert '[Content_Types].xml' not in self.pack
		assert self.pack.content_types

	def test_add_part(self):
		self.test_content_types()
		self.part = part = Part(self.pack, '/foo')
		self.pack[part.name] = part
	
	def test_relate_part(self):
		self.test_add_part()
		r = Relationship(self.pack, '/foo', 'http://polimetrix.com/part')
		self.pack.relationships.add(r)
	
	def test_related(self):
		self.test_relate_part()
		assert self.pack.related('http://polimetrix.com/part')[0] == self.part

	def test_add_override_false(self):
		self.test_create()
		p = SamplePart(self.pack, '/pmx/samp.vpart')
		self.pack.add(p, override=False)
		ct = self.pack.content_types.find_for('/pmx/samp.vpart')
		assert ct is not None
		
	def test_add_no_override(self):
		self.test_create()
		p = SamplePart(self.pack, '/pmx/samp.main')
		p.content_type = "app/pmxmain+xml"
		self.pack.add(p)
		ct = self.pack.content_types.find_for('/pmx/samp.main') 
		assert ct is not None
		assert ct.name == 'app/pmxmain+xml'

class TestContentTypes:
	def test_no_duplicates_in_output(self):
		cts = ContentTypes()
		cts.add(ContentType.Default('application/xml', 'xml'))
		cts.add(ContentType.Default('application/xml', 'xml'))
		assert len(cts) == 1
		assert len(re.findall('application/xml', cts.dump())) == 1
		assert len(re.findall('Extension="xml"', cts.dump())) == 1
