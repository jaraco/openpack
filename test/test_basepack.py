import py.test
import re

from common import SamplePart
from openpack.basepack import *

class TestBasicPart(object):
	invalid_names = ('abc', '/abc/', '/foo/bar.', '/bar/./abc.xml')

	def test_good_names(self):
		for n in ('/abc', '/foo/bar', '/foo-1/bar.xml'):
			yield self.check_name, n
	
	def check_name(self, name, should_fail=False):
		if should_fail:
			py.test.raises(ValueError, Part, None, name)
		else:
			p = Part(None, name)

	def test_bad_names(self):
		for n in self.invalid_names:
			yield self.check_name, n, True

	def test_reset_part_name_to_invalid_name(self):
		part = SamplePart(None, '/foo')
		for name in self.invalid_names:
			py.test.raises(ValueError, setattr, part, 'name', name)

	def test_part_rels(self):
		p = Part(None, '/word/document.xml')
		assert isinstance(p.relationships, Relationships)

	def test_cant_dump_part_without_data(self):
		part = Part(None, '/word/document.xml')
		py.test.raises(BaseException, part.dump)

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
		assert isinstance(ct, ContentType.Default)
		assert ct is not None
		assert ct.key == 'vpart'
		assert ct.name == p.content_type
		
	def test_add_no_override(self):
		self.test_create()
		p = SamplePart(self.pack, '/pmx/samp.main', content_type='app/pmxmain+xml')
		self.pack.add(p)
		ct = self.pack.content_types.find_for('/pmx/samp.main') 
		assert isinstance(ct, ContentType.Override)
		assert ct is not None
		assert ct.key == p.name
		assert ct.name == p.content_type

	def test_get_parts_by_content_type(self):
		pack = Package()
		part = SamplePart(pack, '/pmx/samp.main')
		pack.add(part)
		parts = pack.get_parts_by_content_type(part.content_type)
		assert parts.next() is part
		py.test.raises(StopIteration, parts.next)
		ct = pack.content_types.find_for(part.name)
		parts = pack.get_parts_by_content_type(ct)
		assert parts.next() is part
		py.test.raises(StopIteration, parts.next)

	def test_get_parts_by_class(self):
		pack = Package()
		part = SamplePart(pack, '/pmx/samp.main')
		pack.add(part)
		parts = pack.get_parts_by_class(SamplePart)
		assert parts.next() is part
		py.test.raises(StopIteration, parts.next)

class TestContentTypes:
	def test_no_duplicates_in_output(self):
		cts = ContentTypes()
		cts.add(ContentType.Default('application/xml', 'xml'))
		cts.add(ContentType.Default('application/xml', 'xml'))
		assert len(cts) == 1
		assert len(re.findall('application/xml', cts.dump())) == 1
		assert len(re.findall('Extension="xml"', cts.dump())) == 1

class TestDefaultNamedPart:
	def test_default_named_part(self):
		class PartToTest(DefaultNamed, Part):
			default_name = '/part_name'
		pack = Package()
		part = PartToTest(pack)
		assert part.name == PartToTest.default_name

	def test_default_named_part_missing_attribute(self):
		class PartToTest(DefaultNamed, Part):
			pass
		pack = Package()
		py.test.raises(AttributeError, PartToTest, pack)
