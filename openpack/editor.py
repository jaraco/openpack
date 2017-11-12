from __future__ import with_statement, print_function

import argparse
import tempfile
import os
import sys
import posixpath
import inspect
import subprocess
from zipfile import ZipFile

from lxml import etree

from .zippack import ZipPackage as Package


def part_edit_cmd():
	'Edit a part from an OOXML Package without unzipping it'
	parser = argparse.ArgumentParser(description=inspect.getdoc(part_edit_cmd))
	parser.add_argument(
            'path',
            help='Path to part (including path to zip file, i.e. ./file.zipx/part)')
	parser.add_argument(
            '--reformat-xml',
            action='store_true',
            help='run the content through an XML pretty-printer first for improved editability')
	args = parser.parse_args()
	part_edit(args.path, args.reformat_xml)


def pack_dir_cmd():
	'List the contents of a subdirectory of a zipfile'
	parser = argparse.ArgumentParser(description=inspect.getdoc(part_edit_cmd))
	help = 'Path to list (including path to zip file, i.e. ./file.zipx or ./file.zipx/subdir)'
	parser.add_argument('path', help=help)
	args = parser.parse_args()
	for item, is_file in sorted(list_contents(args.path)):
		prefix = 'd ' if not is_file else '  '
		msg = prefix + item
		print(msg)


class EditableFile(object):
	def __init__(self, data=None):
		self.data = data

	def __enter__(self):
		fobj, self.name = tempfile.mkstemp()
		if self.data:
			os.write(fobj, self.data)
		os.close(fobj)
		return self

	def read(self):
		with open(self.name, 'rb') as f:
			return f.read()

	def __exit__(self, *tb_info):
		os.remove(self.name)

	def edit(self, ipath):
		self.changed = False
		with self:
			editor = self.get_editor(ipath)
			cmd = [editor, self.name]
			try:
				res = subprocess.call(cmd)
			except Exception as e:
				print("Error launching editor %(editor)s" % vars())
				print(e)
				return
			if res != 0:
				return
			new_data = self.read()
			if new_data != self.data:
				self.changed = True
				self.data = new_data

	@staticmethod
	def get_editor(filepath):
		"""
		Give preference to an XML_EDITOR or EDITOR defined in the
		environment. Otherwise use notepad on Windows and edit on other
		platforms.
		"""
		default_editor = ['edit', 'notepad'][sys.platform.startswith('win32')]
		return os.environ.get('XML_EDITOR',
                        os.environ.get('EDITOR', default_editor))


def part_edit(path, reformat_xml):
	file, ipath = find_file(path)
	pkg = Package.from_file(file)
	if ipath.startswith('[Content-Types]'):
		part = pkg.content_types
	else:
		part = pkg['/' + ipath]
	data = part.dump()
	if reformat_xml:
		data = etree.tostring(etree.fromstring(data), pretty_print=True)
	ef = EditableFile(data)
	ef.edit(ipath)
	if ef.changed:
		part.load(ef.data)
		pkg.save()


def list_contents(path):
	file, target_path = find_file(path)
	pkg = ZipFile(file)

	def is_contained_in_target(item):
		return posixpath.join(target_path, item) in pkg.namelist()

	def get_subdir_of_target(item):
		while True:
			item, item_name = posixpath.split(item)
			if item == target_path:
				return item_name
			if not item:
				break
	subitems = set(filter(None, map(get_subdir_of_target, pkg.namelist())))
	subitems_is_file = map(is_contained_in_target, subitems)
	return zip(subitems, subitems_is_file)


def split_all(path):
	"""
	recursively call os.path.split until we have all of the components
	of a pathname suitable for passing back to os.path.join.
	"""
	drive, path = os.path.splitdrive(path)
	head, tail = os.path.split(path)
	terminators = [os.path.sep, os.path.altsep, '']
	parts = split_all(head) if head not in terminators else [head]
	return [drive] + parts + [tail]


def find_file(path):
	"""
	Given a path to a part in a zip file, return a path to the file and
	the path to the part.

	Assuming /foo.zipx exists as a file,

	>>> find_file('/foo.zipx/dir/part') # doctest: +SKIP
	('/foo.zipx', '/dir/part')

	>>> find_file('/foo.zipx') # doctest: +SKIP
	('/foo.zipx', '')
	"""
	path_components = split_all(path)

	def get_assemblies():
		"""
		Enumerate the various combinations of file paths and part paths
		"""
		for n in range(len(path_components), 0, -1):
			file_c = path_components[:n]
			part_c = path_components[n:] or ['']
			yield (os.path.join(*file_c), posixpath.join(*part_c))
	for file_path, part_path in get_assemblies():
		if os.path.isfile(file_path):
			return file_path, part_path
