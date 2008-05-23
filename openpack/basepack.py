"""An Open Packaging Conventions implementation.
"""

import os
from cStringIO import StringIO
from lxml.etree import Element, ElementTree, fromstring, tostring 
from string import Template
from UserDict import DictMixin

from util import validator, parse_tag, handle

ooxml_namespaces = {
	'cp':'http://schemas.openxmlformats.org/package/2006/metadata/core-properties',
	'dc':'http://purl.org/dc/elements/1.1/',
	'dcterms':'http://purl.org/dc/terms/',
	'dcmitype':'http://purl.org/dc/dcmitype/',
	'xsi':'http://www.w3.org/2001/XMLSchema-instance',
	'v':"urn:schemas-microsoft-com:vml",
	'w':"http://schemas.openxmlformats.org/wordprocessingml/2006/main",
}

class Relational(object):
	"A mixin class for packages and parts; both support relationships."
	def relate(self, part, id=None):
		"""Relate this package component to the supplied part."""
		name = part.name[len(self.base):].lstrip('/')
		rel = Relationship(self, name, part.rel_type, id=id)
		self.relationships.add(rel)
		return rel

	def related(self, reltype):
		"""Return a list of parts related to this one via reltype."""
		parts = []
		package = getattr(self, 'package', None) or self
		for rel in self.relationships.types.get(reltype, []):
			parts.append(package[os.path.join(self.base, rel.target)])
		return parts

	def _load_rels(self, source):
		"""Load relationships from source XML."""
		elem = fromstring(source)
		for rel in elem:
			mode = rel.get('TargetMode')
			target = rel.get('Target')
			rtype = rel.get('Type')
			id = rel.get('Id')
			relationship = Relationship(self, target, rtype, id, mode)
			self.relationships.add(relationship)

class Package(DictMixin, Relational):
	"""A base class for an OPC package.

	Handles processing provided XML into the core components of a Package:
	 * Relationships
	 * Content-Types
	 * Parts
	
	Subclasses should overload open(...) and save(...) to read and write
	data to and from various physical package formats.

	Instances of this class support dict-style access to parts via their
	part-names.
	"""

	def __init__(self, name=None):
		self.parts = {}
		self.base = '/'
		self.relationships = rels = Relationships(self, self)
		self[rels.name] = rels
		self.content_types = ContentTypes()
		self.core_properties = None
		self.start_part = None
		self.name = name
	
	def __setitem__(self, name, part):
		self._validate_part(name, part)
		self.parts[part.name] = part
		try:
			if part.relationships:
				self.parts[part.relationships.name] = part.relationships
		except ValueError:
			pass

	def __getitem__(self, name):
		"""Returns a part from the given URL."""
		return self.parts[name]

	def __delitem__(self, name):
		del self.parts[name]

	def keys(self):
		return self.parts.keys()

	def add(self, part, override=True):
		"""Add a part to the package.

		It will also add a content-type - by default an override.  If
		override is False then it will add a content-type for the extension
		if on isn't already present.
		"""
		self[part.name] = part
		if override:
			self.content_types.add_override(part)
		else:
			ext = part.name.rsplit('.', 1)[1]
			self.content_types.add(DefaultType(part.content_type, ext))

	@validator
	def _validate_part(self, name, part):
		# 8.1.1.1 -   A package implementer shall neither create nor 
		# recognize a part with a part name derived from another part name by
		# appending segments to it
		for cname in self:
			assert not cname.startswith(name), \
					'The name %s is a derivative of %s' % (name, cname)
		assert name == part.name, "%s != %s" % (name, part.name)
		return part

	def save(self):
		raise NotImplementedError("Subclasses must implement save.")

	def open(self):
		raise NotImplementedError("Subclasses must implement open.")
		# something like this ...
		self._load_content_types(ct_xml)
		self._load_package_rels(rel_xml)
		for rel in self.relationships:
			self._load_part(rel.name, some_file_like_object)

	def _load_content_types(self, source):
		"""Load up the content_types object with value from source XML."""
		elem = fromstring(source)
		for ce in elem:
			ns, raw_tag = parse_tag(ce.tag)
			if raw_tag == 'Default':
				t = DefaultType(ce.get('ContentType'), ce.get('Extension'))
			elif raw_tag == 'Override':
				t = OverrideType(ce.get('ContentType'), ce.get('PartName'))
			else:
				raise ValueError('Invalid Types child element: %s' % raw_tag)
			self.content_types.add(t)

	def _load_part(self, name, fp):
		"""This is the default loader for unhandled parts.

		Parts can have custom loading logic by defining their own package
		level method decorated with @handle(relationship_type).  See
		_load_core_properties in this class for an example.
		"""
		try:
			ext = name.rsplit('.', 1)[1]
		except IndexError:
			ext = None
		if name in self.content_types.overrides:
			ct = self.content_types.overrides.get(name)
		elif ext in self.content_types.defaults:
			ct = self.content_types.defaults[ext]
		else:
			ct = None
		if ct:
			part = Part(self, name, ct, fp=fp)
			self[name] = part

	@handle('http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties')
	def _load_core_props(self, name, fp):
		self.core_properties = cp = CoreProperties(self, name)
		cp.element = fromstring(fp.read())
		self[cp.name] = cp

	def map_name(self, name):
		"Subclasses can override this for custom name mapping."
		return name

	def __repr__(self):
		return "Package-%s" % id(self)

class Part(Relational):
	"""Parts are the building blocks of OOXML files.

	All Part subclasses need to define their content-type in a
	content_type attribute.  Most will also need a relationship-type 
	(defined in the rel_type attribute).  See the documentation for the
	part that you are implementing for the proper values for those attributes.
	"""
	content_type = None
	rel_type = None

	def __init__(self, package, name, growth_hint=None, fp=None):
		self.name = self._validate_name(name)
		self.base = os.path.dirname(self.name)
		self.package = package
		self.growth_hint = growth_hint
		if not isinstance(self, Relationships):
			self.relationships = Relationships(self.package, self)
		if fp is None:
			fp = StringIO()
		self.fp = fp
		self.encoding = None

	@validator
	def _validate_name(self, name):
		assert name
		assert name[0] == '/', "%s does not start with a '/'" % name
		assert name[-1] != '/', "%s ends with a '/'" % name
		#TODO: test for empty segments
		#TODO: test for only pchar characters (RFC 3986)
		for segment in name[1:].split('/'):
			#TODO: test for percent encoded slash and unreserved chars
			assert segment[-1] != '.'
			assert segment != '.'
		return name
	
	def __iter__(self):
		"""Should return an iterator for the underlying content."""
		return iter(self.fp)

	def dump(self):
		"""Return the raw bytes of the Part."""
		self.fp.seek(0)
		return self.fp.read()

class Relationship(object):
	"""Represents an OPC relationship between a Package/Part and another Part.

	source : a Package or Part instance
	target : the URL for the target part
	reltype : the type that defines the relationship
	id : a unique identifier for this relationship
	mode : should be one of "Internal" or "External" 
	"""
	def __init__(self, source, target, reltype, id=None, mode=None):
		self.source = self._validate_source(source)
		self.target = self._validate_target(target)
		self.id = self._validate_id(id)
		self.mode = self._validate_mode(mode or "Internal")
		self.type = reltype
   
	def __repr__(self):
		args = (self.source, self.target, self.type, self.id, self.mode)
		return "Relationship(self, %r, %r, %r, %r, %r)" % args

	@validator
	def _validate_source(self, source):
		assert isinstance(source, (Package, Part))
		return source
	
	@validator
	def _validate_target(self, target):
		assert isinstance(target, basestring), "target must be a part name"
		return target

	@validator
	def _validate_mode(self, mode):
		assert mode in ("Internal", "External")
		return mode

	@validator
	def _validate_id(self, id):
		if id is None:
			return self._generate_id()
		# TODO: The Id type is xsd:ID and it shall conform to the naming 
		# restrictions for xsd:ID as specified in the W3C Recommendation 
		# "XML Schema Part 2: Datatypes."  
		return id

	def _generate_id(self):
		return "d%s" % os.urandom(4).encode('hex')

class Relationships(Part):
	"""A collection of Package or Part Relationships."""
	xmlns = "{http://schemas.openxmlformats.org/package/2006/relationships}"
	content_type = "application/vnd.openxmlformats-package.relationships+xml"
	rel_type = None

	def __init__(self, package, source, encoding=None):
		name = self._name_from_source(source)
		Part.__init__(self, package, name)
		self.ids = set()
		self.children = set()
		self.types = {}
		self.encoding = encoding or 'utf-8'

	class relationships(object):
		def __get__(self, instance, owner):
			raise ValueError("Relationship parts have no relationships.")

		def __set__(self, instance, value):
			return
	relationships = relationships()
  
	def dump(self):
		if not self.children:
			return ''
		rels = Element(self.xmlns + 'Relationships', nsmap={None:self.xmlns.strip('{}')})
		for rel in self:
			rels.append(Element(
				'Relationship',
				TargetMode=rel.mode,
				Target=rel.target,
				Type=rel.type,
				Id=rel.id,
			))
		return tostring(rels, encoding=self.encoding)

	def __iter__(self):
		return iter(self.children)

	def __repr__(self):
		return "\n".join([repr(c) for c in self.children])

	def add(self, rel):
		self.ids.add(self._validate_id(rel.id))
		self.children.add(rel)
		self.types.setdefault(rel.type, []).append(rel)

	@validator
	def _validate_id(self, id):
		# The value of the Id attribute shall be
		# unique within the Relationships part.
		assert id not in self.ids
		return id

	def _name_from_source(self, source):
		if isinstance(source, Package):
			return "/_rels/.rels"
		base, item = os.path.split(source.name)
		return os.path.join(base, '_rels/%s.rels' % item)

class ContentTypes(object):
	"""A container for managing Package content types."""
	
	xmlns = '{http://schemas.openxmlformats.org/package/2006/content-types}'
	def __init__(self, encoding=None):
		self.children = []
		self.defaults = {}
		self.overrides = {}
		self.encoding = encoding or 'utf-8'

	def add_override(self, part):
		ct = OverrideType(part.content_type, part.name)
		self.add(ct)
		return ct

	def add(self, ct):
		if isinstance(ct, DefaultType):
			self.defaults[ct.extension] = self._validate_default(ct)
		elif isinstance(ct, OverrideType):
			self.overrides[ct.part_name] = self._validate_override(ct)
		self.children.append(ct)
   
	def dump(self):
		types = Element(self.xmlns + 'Types', nsmap={None:self.xmlns.strip('{}')})
		for ct in self.children:
			types.append(ct.to_element())
		return tostring(types, encoding=self.encoding)
		
	@validator
	def _validate_default(self, ct):
		assert ct.extension not in self.defaults
		return ct

	@validator
	def _validate_override(self, ct):
		assert ct.part_name not in self.overrides
		return ct

class DefaultType(object):
	"""A Default content type, base on a file extension."""
	def __init__(self, content_type, extension):
		self.content_type = content_type
		self.extension = extension

	def to_element(self):
		elem = Element(
			'Default',
			Extension=self.extension,
			ContentType=self.content_type,
		)
		return elem

	def __repr__(self):
		return "DefaultType(%r, %r)" % (self.content_type, self.extension)

class OverrideType(object):
	"""An Override content type, based on a part name."""
	def __init__(self, content_type, part_name):
		self.content_type = content_type
		self.part_name = part_name

	def to_element(self):
		elem = Element(
			'Override',
			PartName=self.part_name,
			ContentType=self.content_type,
		)
		return elem

	def __repr__(self):
		return "OverrideType(%r, %r)" % (self.content_type, self.part_name)

class CoreProperties(Part):
	content_type = "application/vnd.openxmlformats-package.core-properties+xml"
	rel_type = "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties"

	def __init__(self, package, name, encoding=None):
		Part.__init__(self, package, name)
		self.encoding = encoding or 'utf-8'
		self.element = None

	def dump(self):
		if self.element:
			return tostring(self.element, encoding=self.encoding)
		return ''

