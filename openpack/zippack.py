import time
import posixpath
import functools
import io
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

import six

from .basepack import Package, Part, Relationships


def to_zip_name(name):
	"""
	Packages store items with names prefixed with slashes, but zip files
	prefer them without. This method strips the leading slash.
	"""
	return name.lstrip('/')


class ZipPackage(Package):
	@classmethod
	def from_file(cls, filename):
		package = cls.from_stream(open(filename, 'rb'))
		package.filename = filename
		return package

	@classmethod
	def from_stream(cls, stream):
		package = cls()
		package._load(stream)
		return package

	def _load(self, stream):
		zf = ZipFile(stream)
		self._load_content_types(zf.read('[Content_Types].xml'))
		rels_path = posixpath.join('_rels', '.rels')
		self._load_rels(zf.read(rels_path))

		def ropen(item):
			"read item and recursively open its children"
			if isinstance(item, Relationships):
				return
			if isinstance(item, Part):
				base, rname = posixpath.split(to_zip_name(item.name))
				relname = posixpath.join(base, '_rels', '%s.rels' % rname)
				if relname in zf.namelist():
					item._load_rels(zf.read(relname))
			for rel in item.relationships:
				pname = posixpath.join(item.base, rel.target)
				if pname in self:
					# This item is already in self.
					continue
				target_path = to_zip_name(pname)
				data = b"".join(self._get_matching_segments(zf, target_path))
				new_part = self._load_part(rel.type, pname, data)
				if new_part:
					ropen(new_part)
		ropen(self)
		zf.close()

	def save(self, target=None):
		"""
		Save this package to target, which should be a filename or open
		file stream. If target is not supplied, and this package has a
		filename attribute (such as when this package was created from
		an existing file), it will be used.
		"""
		target = target or getattr(self, 'filename', None)
		if isinstance(target, six.string_types):
			self.filename = target
			target = open(target, 'wb')
		if target is None:
			msg = (
				"Target filename required if %s was not opened from a file"
				% self.__class__.__name__
			)
			raise ValueError(msg)
		self._store(target)

	def as_stream(self):
		"""
		Return a zipped package as a readable stream
		"""
		stream = io.BytesIO()
		self._store(stream)
		stream.seek(0)
		return stream

	def _store(self, stream):
		zf = _ZipPackageZipFile(stream, mode='w', compression=ZIP_DEFLATED)
		zf.write_part('[Content_Types].xml', self.content_types.dump())
		zf.write_part('_rels/.rels', self.relationships.dump())
		for name in self.parts:
			if name == '/_rels/.rels':
				continue
			part = self[name]
			try:
				zf.write_part(to_zip_name(name), part.dump())
			except BaseException:
				# silently ignore any part that fails to generate any
				#  content.
				pass

	def _get_matching_segments(self, zf, name):
		"""
		Return a generator yielding each of the segments who's names
		match name.
		"""
		for n in zf.namelist():
			if n.startswith(name):
				yield zf.read(n)


class _ZipPackageZipFile(ZipFile):
	"""
	A wrapper around the zipfile to capture some of the common
	usage of a ZipFile for ZipPackages.
	"""

	def __init__(self, *args, **kwargs):
		ZipFile.__init__(self, *args, **kwargs)
		# each piece of content will be created with the same date_time
		# attribute (set to now)
		now = time.localtime(time.time())
		self.zip_info_factory = functools.partial(ZipInfo, date_time=now)

	def write_part(self, name, content):
		USER_READ_WRITE = 25165824
		SYSUNIX = 3
		info = self.zip_info_factory(name)
		info.create_system = SYSUNIX
		info.flag_bits = 8
		info.external_attr = USER_READ_WRITE
		info.compress_type = ZIP_DEFLATED
		self.writestr(info, content)


if __name__ == '__main__':
	zp = ZipPackage.from_file('../data/whatever.docx')
	print(zp)
	print(zp.relationships)
