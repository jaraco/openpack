import os
import time
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

from basepack import Package, Part, Relationship, Relationships
from util import get_handler

USER_READ_WRITE = 25165824
SYSUNIX = 3

class ZipPackage(Package):
	def __init__(self, name):
		Package.__init__(self, name)
		self._zipfile = None
		if os.path.exists(name):
			self.open()

	def open(self):
		self._zipfile = zf = ZipFile(self.name)
		self._load_content_types(zf.read('[Content_Types].xml'))
		self._load_rels(zf.read('_rels/.rels'))
		def ropen(item):
			if isinstance(item, Relationships):
				return
			if isinstance(item, Part):
				base, rname = os.path.split(item.name)
				relname = "%s/_rels/%s.rels" % (base[1:], rname)
				if relname in zf.namelist():
					item._load_rels(zf.read(relname))
			for rel in item.relationships:
				data = []
				for name in self.map_name(rel.target):
					data.append(zf.read(name))
				data = "".join(data)
				pname = os.path.join(item.base, rel.target)
				# get a handler for the relationship type or use a default
				add_part = get_handler(rel.type, ZipPackage._load_part)
				add_part(self, pname, data)
				ropen(self[pname])
		ropen(self)
		zf.close()

	def save(self, target=None):
		localtime = time.localtime(time.time())
		zf = ZipFile(target or self.name, mode='w', compression=ZIP_DEFLATED)
		ct_info = ZipInfo('[Content_Types].xml', localtime)
		ct_info.create_system = SYSUNIX
		ct_info.flag_bits = 8
		ct_info.external_attr = USER_READ_WRITE
		ct_info.compress_type = ZIP_DEFLATED
		zf.writestr(ct_info, self.content_types.dump())
		rel_info = ZipInfo('_rels/.rels', localtime)
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
			part_info = ZipInfo(name[1:], localtime)
			part_info.create_system = SYSUNIX
			part_info.flag_bits = 8
			part_info.external_attr = USER_READ_WRITE
			part_info.compress_type = ZIP_DEFLATED
			zf.writestr(part_info, content)

	def map_name(self, name):
		return [n for n in self._zipfile.namelist() if n.startswith(name)]

if __name__ == '__main__':
	zp = ZipPackage('../data/whatever.docx')
	zp.open()
	print zp
	print zp.relationships

