import os
import time
import posixpath
import functools
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

from basepack import Package, Part, Relationship, Relationships
from util import get_handler

USER_READ_WRITE = 25165824
SYSUNIX = 3

def to_zip_name(name):
	"""
	Packages store items with names prefixed with slashes, but zip files
	prefer them without. This method strips the leading slash.
	"""
	return name.lstrip('/')
	
class ZipPackage(Package):
	def __init__(self, name):
		Package.__init__(self, name)
		self._zipfile = None
		if os.path.exists(name):
			self.open()

	def open(self):
		self._zipfile = zf = ZipFile(self.name)
		self._load_content_types(zf.read('[Content_Types].xml'))
		rels_path = posixpath.join('_rels', '.rels')
		self._load_rels(zf.read(rels_path))
		def ropen(item):
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
				data = "".join(self._get_matching_segments(target_path))
				# get a handler for the relationship type or use a default
				add_part = get_handler(rel.type, ZipPackage._load_part)
				add_part(self, pname, data)
				ropen(self[pname])
		ropen(self)
		zf.close()

	def save(self, target=None):
		now = time.localtime(time.time())
		ZipInfoNow = functools.partial(ZipInfo, date_time = now)
		zf = ZipFile(target or self.name, mode='w', compression=ZIP_DEFLATED)
		ct_info = ZipInfoNow('[Content_Types].xml')
		ct_info.create_system = SYSUNIX
		ct_info.flag_bits = 8
		ct_info.external_attr = USER_READ_WRITE
		ct_info.compress_type = ZIP_DEFLATED
		zf.writestr(ct_info, self.content_types.dump())
		rel_info = ZipInfoNow('_rels/.rels')
		rel_info.create_system = SYSUNIX
		rel_info.flag_bits = 8
		rel_info.external_attr = USER_READ_WRITE
		rel_info.compress_type = ZIP_DEFLATED
		zf.writestr(rel_info, self.relationships.dump())
		for name in self.parts:
			if name == '/_rels/.rels':
				continue
			part = self[name]
			content = part.dump()
			if not content:
				continue
			part_info = ZipInfoNow(to_zip_name(name))
			part_info.create_system = SYSUNIX
			part_info.flag_bits = 8
			part_info.external_attr = USER_READ_WRITE
			part_info.compress_type = ZIP_DEFLATED
			zf.writestr(part_info, content)

	def _get_matching_segments(self, name):
		"""
		Return a generator yielding each of the segments who's names
		match name.
		"""
		for n in self._zipfile.namelist():
			if n.startswith(name):
				yield self._zipfile.read(n)

if __name__ == '__main__':
	zp = ZipPackage('../data/whatever.docx')
	zp.open()
	print zp
	print zp.relationships

