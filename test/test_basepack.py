import py.test

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
		pack0 = Package()
		pack1 = Package('foo')
		self.pack = pack1

	def test_package_rels(self):
		assert self.pack.relationships
		assert self.pack['/_rels/.rels']
		assert self.pack.relationships == self.pack['/_rels/.rels']

	def test_content_types(self):
		# the content types part is not addressable
		assert '[Content_Types].xml' not in self.pack
		assert self.pack.content_types

	def test_add_part(self):
		self.part = part = Part(self.pack, '/foo')
		self.pack[part.name] = part
	
	def test_relate_part(self):
		r = Relationship(self.pack, '/foo', 'http://polimetrix.com/part')
		self.pack.relationships.add(r)
	
	def test_related(self):
		assert self.pack.related('http://polimetrix.com/part')[0] == self.part

	def test_add_no_override(self):
		p = SamplePart(self.pack, '/pmx/samp.vpart')
		self.pack.add(p, override=False)
		assert 'vpart' in self.pack.content_types.defaults
		
	def test_add_no_override(self):
		p = SamplePart(self.pack, '/pmx/samp.main')
		p.content_type = "app/pmxmain+xml"
		self.pack.add(p)
		assert '/pmx/samp.main' in self.pack.content_types.overrides

