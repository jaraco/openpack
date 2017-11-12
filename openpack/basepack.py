"""An Open Packaging Conventions implementation.
"""

import os
import posixpath
import datetime
import logging
import collections
import codecs
from collections import defaultdict
from jaraco.collections import FoldedCaseKeyedDict

import six
from lxml.etree import Element, fromstring, tostring
from lxml.builder import ElementMaker as _ElementMaker

from .util import validator, parse_tag, get_ext

log = logging.getLogger(__name__)

# even though Element looks like a class name, it's actually a function. To
#   get the actual class, construct an instance and grab its class.
ElementClass = Element('__').__class__

ooxml_namespaces = dict(
	cp='http://schemas.openxmlformats.org/package/2006/metadata/'
  		'core-properties',
	dc='http://purl.org/dc/elements/1.1/',
	dcterms='http://purl.org/dc/terms/',
	dcmitype='http://purl.org/dc/dcmitype/',
	xsi='http://www.w3.org/2001/XMLSchema-instance',
)


class Relational(object):
	"A mixin class for packages and parts; both support relationships."

	def relate(self, part, id=None):
		"""Relate this package component to the supplied part."""
		assert part.name.startswith(self.base)
		name = part.name[len(self.base):].lstrip('/')
		rel = Relationship(self, name, part.rel_type, id=id)
		self.relationships.add(rel)
		return rel

	def related(self, reltype):
		"""Return a list of parts related to this one via reltype."""
		parts = []
		package = getattr(self, 'package', None) or self
		for rel in self.relationships.types.get(reltype, []):
			parts.append(package[posixpath.join(self.base, rel.target)])
		return parts

	def _load_rels(self, source):
		"""Load relationships from source XML."""
		# don't get confused here - the original source is string data;
		#  the parameter source below is a Part object
		self.relationships.load(source=self, data=source)


class Package(collections.MutableMapping, Relational):
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

	def __init__(self):
		self.parts = {}
		self.base = '/'
		self.relationships = rels = Relationships(self, self)
		self[rels.name] = rels
		self.content_types = ContentTypes()
		self.content_types.add(ContentType.Default(rels.content_type, 'rels'))

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

	def __iter__(self):
		return iter(self.parts)

	def __len__(self):
		return len(self.parts)

	def keys(self):
		return self.parts.keys()

	def add(self, part, override=True):
		"""Add a part to the package.

		It will also add a content-type - by default an override.  If
		override is False then it will add a content-type for the extension
		if one isn't already present.
		"""
		ct_add_method = [
			self.content_types.add_default,
			self.content_types.add_override,
                ][override]
		self[part.name] = part
		ct_add_method(part)

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
		# something like this:
		"""
		self._load_content_types(ct_xml)
		self._load_package_rels(rel_xml)
		for rel in self.relationships:
			self._load_part(rel.name, some_file_like_object)
		"""

	def _load_content_types(self, source):
		"""Load up the content_types object with value from source XML."""
		self.content_types.update(ContentTypes.load(source))

	def _load_part(self, rel_type, name, data):
		"""
		Load a part into this package based on its relationship type
		"""
		if self.content_types.find_for(name) is None:
			log.warning('no content type found for part %(name)s' % vars())
			return
		cls = Part.classes_by_rel_type[rel_type]
		part = cls(self, name)
		part.load(data)
		self[name] = part
		return part

	def __repr__(self):
		return "Package-%s" % id(self)

	def get_parts_by_class(self, cls):
		"""
		Return all parts of this package that are instances of cls
		(where cls is passed directly to isinstance, so can be a class
		or sequence of classes).
		"""
		return (part for part in self.parts.values() if isinstance(part, cls))

	def get_parts_by_content_type(self, content_type):
		# first find any parts who's registered type matches or who's
		#  content_type attribute matches
		return (
			part
			for part in self.parts.values()
			if self.content_types.find_for(part.name) == content_type
			or part.content_type == content_type
                )

	@property
	def core_properties(self):
		return next(self.get_parts_by_class(CoreProperties))


class DefaultNamed(object):
	"""
	Mix-in for Parts that have a default name. Subclasses should include
	a 'default_name' attribute, which will be used during construction
	if a name is not explicitly defined.
	"""

	def __init__(self, package, name=None, *args, **kwargs):
		name = name or self.default_name
		super(DefaultNamed, self).__init__(package, name, *args, **kwargs)


class RelationshipTypeHandler(type):
	"""
	A metaclass designed to register new Part classes that handle
	particular relationship types. Whenever a new subclass of Part is
	created, its rel_type attribute will be mapped to that class.

	Subsequently, Part.classes_by_rel_type will be a mapping of
	relationship-type to the appropriate class for that rel-type.
	"""
	def __new__(mcs, name, bases, attrs):
		"""
		This is called when a new class is created of this type
		"""
		# Allow the new class to be created
		cls = type.__new__(mcs, name, bases, attrs)
		# if the class (or its parent) doesn't already have a mapping
		#  of relationship type to class, create one (with this new
		#  class being the default).
		if not hasattr(cls, 'classes_by_rel_type'):
			cls.classes_by_rel_type = defaultdict(lambda: cls)
		rt = attrs.get('rel_type', None)
		if rt:
			cls.classes_by_rel_type[rt] = cls
		return cls


@six.add_metaclass(RelationshipTypeHandler)
class Part(Relational):
	"""
	Parts are the building blocks of OOXML files.

	All Part subclasses need to define their content-type in a
	content_type attribute.  Most will also need a relationship-type
	(defined in the rel_type attribute).  See the documentation for the
	part that you are implementing for the proper values for those attributes.
	"""
	content_type = None
	rel_type = None

	def __init__(self, package, name, **kwargs):
		#map(functools.partial(setattr, self), *kwargs.items())
		for key, value in kwargs.items():
			setattr(self, key, value)
		self.name = name
		self.package = package
		if not isinstance(self, Relationships):
			self.relationships = Relationships(self.package, self)

	@property
	def base(self):
		return posixpath.dirname(self.name)

	@validator
	def _set_name(self, name):
		assert name
		assert name[0] == '/', "%s does not start with a '/'" % name
		assert name[-1] != '/', "%s ends with a '/'" % name
		# TODO: test for empty segments
		# TODO: test for only pchar characters (RFC 3986)
		for segment in name[1:].split('/'):
			# TODO: test for percent encoded slash and unreserved chars
			assert segment[-1] != '.'
			assert segment != '.'
		self._name = name

	def _get_name(self):
		return self._name

	name = property(_get_name, _set_name)

	def __iter__(self):
		"""Should return an iterator for the underlying content."""
		return iter(self.data or [])

	def dump(self):
		"""Return the raw bytes of the Part."""
		data = self.data
		if isinstance(data, ElementClass):
			data = tostring(data, encoding='utf-8', pretty_print=True)
		if isinstance(data, six.text_type):
			return data.encode('utf-8')
		return data

	def load(self, data):
		self.data = data


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
		return "Relationship(%r, %r, %r, %r, %r)" % args

	@validator
	def _validate_source(self, source):
		assert isinstance(source, (Package, Part))
		return source

	@validator
	def _validate_target(self, target):
		assert isinstance(target, six.string_types), "target must be a part name"
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

	@staticmethod
	def _generate_id():
		return "d%s" % codecs.encode(os.urandom(4), 'hex').decode()


class Relationships(Part):
	"""A collection of Package or Part Relationships."""
	xmlns = "{http://schemas.openxmlformats.org/package/2006/relationships}"
	content_type = "application/vnd.openxmlformats-package.relationships+xml"
	rel_type = None

	def __init__(self, package, source, encoding=None):
		"""
		@param source package or part where from which the relationship is
		       derived
		@ptype source Package or Part
		"""
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
		rels = Element(self.xmlns + 'Relationships',
                 nsmap={None: self.xmlns.strip('{}')})
		for rel in self:
			rels.append(Element(
				'Relationship',
				TargetMode=rel.mode,
				Target=rel.target,
				Type=rel.type,
				Id=rel.id,
			))
		return tostring(rels, encoding=self.encoding)

	def load(self, source, data):
		"""
		@param source The source Part for each relationship in this
		              collection
		@ptype source Part
		@param data Relationship XML from a previous dump operation
		@ptype data string
		"""
		elem = fromstring(data)
		for rel in elem:
			mode = rel.get('TargetMode')
			target = rel.get('Target')
			rtype = rel.get('Type')
			id = rel.get('Id')
			relationship = Relationship(source, target, rtype, id, mode)
			self.add(relationship)

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
		base, item = posixpath.split(source.name)
		return posixpath.join(base, '_rels/%s.rels' % item)


class ContentTypes(set):
	"""A container for managing Package content types."""

	xmlns = '{http://schemas.openxmlformats.org/package/2006/content-types}'

	def add_override(self, part):
		ct = ContentType.Override(part.content_type, part.name)
		self.add(ct)
		return ct

	def add_default(self, part):
		ext = get_ext(part.name)
		ct = ContentType.Default(part.content_type, ext)
		self.add(ct)
		return ct

	def dump(self, encoding='utf-8'):
		return tostring(self.to_element(), encoding=encoding)

	@classmethod
	def load(cls, source):
		elem = fromstring(source)
		return cls.from_element(elem)

	def to_element(self):
		elem = Element(self.xmlns + 'Types',
                 nsmap={None: self.xmlns.strip('{}')})
		elem.extend(ct.to_element() for ct in self)
		return elem

	@classmethod
	def from_element(cls, elem):
		ns, tag = parse_tag(elem.tag)
		assert tag == 'Types'
		return cls(map(ContentType.from_element, elem))

	def _item_map(self, class_filter=object):
		return FoldedCaseKeyedDict(
			(item.key, item)
			for item in self
			if isinstance(item, class_filter)
		)
	items = property(_item_map)

	def find_for(self, name):
		"""
		Get the correct content type for a given name
		"""
		map = self.items
		# first search the overrides (by name)
		# then fall back to the defaults (by extension)
		# finally, return None if unmatched
		return map.get(name, None) or map.get(get_ext(name) or None, None)

	# a couple of properties for backward compatibility - please don't
	#  try to write to the resultant collections
	@property
	def defaults(self):
		return self._item_map(ContentType.Default)

	@property
	def overrides(self):
		return self._item_map(ContentType.Override)


class ContentType(object):
	"""
	An abstract content type.
	Each content type has a name, which is a mime-type like
	 application/xml, and a key which refers to the content type.
	"""

	def __init__(self, name, key):
		self.name = name
		self.key = key

	def to_element(self):
		element_name = self.__class__.__name__
		elem = Element(
			element_name,
			ContentType=self.name,
		)
		elem.set(self.key_name, self.key)
		return elem

	@classmethod
	def from_element(cls, element):
		"given an element, parse out the proper ContentType"
		# disambiguate the subclass
		ns, class_name = parse_tag(element.tag)
		class_ = getattr(ContentType, class_name)
		if not class_:
			msg = 'Invalid Types child element: %(class_name)s' % vars()
			raise ValueError(msg)
		# construct the subclass
		key = element.get(class_.key_name)
		name = element.get('ContentType')
		return class_(name, key)

	def __repr__(self):
		params = dict(
			class_name=self.__class__.__name__,
			**self.__dict__
                )
		return "%(class_name)s(%(name)r, %(key)r)" % params

	def __eq__(self, other):
		"""
		This object is equal to another if the other is of the
		same class and the name and key match.
		"""
		attrs = 'name key'.split()
		all_attrs_eq = all(
			getattr(self, attr, None) == getattr(other, attr, None)
			for attr in attrs
                )
		return isinstance(other, self.__class__) and all_attrs_eq

	def __hash__(self):
		return hash((self.name, self.key))


class Default(ContentType):
	"""A Default content type, based on a file extension."""
	key_name = 'Extension'


ContentType.Default = Default
del Default


class Override(ContentType):
	"""An Override content type, based on a part name."""
	key_name = 'PartName'


ContentType.Override = Override
del Override

# Construct E, a convient namespace for making elements in the OOXML
# namespaces.
E = type('E', (object,), dict(
	(key, _ElementMaker(namespace=namespace, nsmap=ooxml_namespaces))
	for key, namespace in ooxml_namespaces.items()
))


class CoreProperties(Part):
	"""
	Core properties on a package, has attributes like 'title', and 'subject'
	"""
	content_type = ("application/"
                 "vnd.openxmlformats-package.core-properties+xml")
	rel_type = ("http://schemas.openxmlformats.org/package/2006/"
             "relationships/metadata/core-properties")
	title = ''
	subject = ''
	creator = ''
	keywords = ''
	description = ''
	last_modified_by = ''
	revision = 1
	created = None
	modified = None
	dt_format = '%Y-%m-%dT%H:%M:%SZ'

	def __init__(self, package, name):
		Part.__init__(self, package, name)

	def load(self, data):
		xml = fromstring(data)

		def DC(tag): return '{%(dc)s}' % ooxml_namespaces + tag

		def CP(tag): return '{%(cp)s}' % ooxml_namespaces + tag

		def DCTERMS(tag): return '{%(dcterms)s}' % ooxml_namespaces + tag

		def identity(x): return x

		def set_attr_if_tag(tag, attr=None, transform=identity):
			if attr is None:
				ns, attr = parse_tag(tag)
			elem = xml.find(tag)
			if elem is not None and elem.text:
				value = transform(elem.text)
				setattr(self, attr, value)
		map(set_attr_if_tag, (
			DC('title'),
			DC('subject'),
			DC('creator'),
			CP('keywords'),
			DC('description'),
                ))
		set_attr_if_tag(CP('revision'), transform=int)
		set_attr_if_tag(CP('lastModifiedBy'), 'last_modified_by')

		def parse_datetime(str):
			try:
				result = datetime.datetime.strptime(str, self.dt_format)
			except ValueError:
				result = str
			return result
		set_attr_if_tag(DCTERMS('created'), transform=parse_datetime)
		set_attr_if_tag(DCTERMS('modified'), transform=parse_datetime)

	def dump(self, encoding='utf-8'):
		return tostring(self.to_element(), encoding=encoding)

	def to_element(self):
		# some datetime handling
		now = datetime.datetime.now()
		if self.created is None:
			self.created = now
		if self.modified is None:
			self.modified = now
		created_str = self.created.strftime(self.dt_format)
		created = E.dcterms.created(created_str)
		created.set('{%(xsi)s}type' % ooxml_namespaces, 'dcterms:W3CDTF')
		modified_str = self.modified.strftime(self.dt_format)
		modified = E.dcterms.modified(modified_str)
		modified.set('{%(xsi)s}type' % ooxml_namespaces, 'dcterms:W3CDTF')
		# create the element
		element = E.cp.coreProperties(
			E.dc.title(self.title),
			E.dc.subject(self.subject),
			E.dc.creator(self.creator),
			E.cp.keywords(self.keywords),
			E.dc.description(self.description),
			E.cp.revision(str(self.revision)),
			E.cp.lastModifiedBy(self.last_modified_by),
			created,
			modified,
		)
		return element

	element = property(to_element)
