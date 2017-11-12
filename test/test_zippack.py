from __future__ import print_function

import os
import tempfile
import pkg_resources
import io

import six

import py.test

from openpack.zippack import ZipPackage

from common import SamplePart


@py.test.fixture
def writable_filename(request):
	"""
	Whenever a function needs a 'writable_filename', create one, but
	be sure it's cleaned up afterward.
	"""
	fobj, name = tempfile.mkstemp()
	os.close(fobj)
	os.remove(name)

	def remove_if_exists():
		if os.path.exists(name):
			os.remove(name)
	request.addfinalizer(remove_if_exists)
	return name


@py.test.fixture
def zippack_sample(request):
	return pkg_resources.resource_string(__name__, 'sample.zipx')


@py.test.fixture
def zippack_sample_filename(request):
	return pkg_resources.resource_filename(__name__, 'sample.zipx')


def test_create():
	"""
	Must be able to create a zip package without any content or
	file system references.
	"""
	ZipPackage()


def test_add_part():
	pack = ZipPackage()
	p = SamplePart(pack, '/test/part.xml')
	pack[p.name] = p
	pack.content_types.add_override(p)
	pack.relate(p)


def test_write_to_part():
	pack = ZipPackage()
	part = p = SamplePart(pack, '/test/part.xml')
	pack[p.name] = p
	pack.content_types.add_override(p)
	pack.relate(p)
	part.data = '<test>hi there</test>'


def test_save(writable_filename):
	pack = ZipPackage()
	part = p = SamplePart(pack, '/test/part.xml')
	pack[p.name] = p
	pack.content_types.add_override(p)
	pack.relate(p)
	part.data = '<test>hi there</test>'
	pack.save(writable_filename)


def test_save_to_stream():
	pack = ZipPackage()
	part = p = SamplePart(pack, '/test/part.xml')
	pack.add(p)
	part.data = '<test>hi there</test>'
	pack.save(io.BytesIO())


def test_create_package_from_existing_file(zippack_sample_filename):
	ZipPackage.from_file(zippack_sample_filename)


def test_create_package_from_stream(zippack_sample):
	"""
	Not everybody wants to create a package from a file system object.
	Make sure the packages can be created from a stream.
	"""
	input_stream = io.BytesIO(zippack_sample)
	ZipPackage.from_stream(input_stream)


def test_store_empty_package():
	pack = ZipPackage()
	data = io.BytesIO()
	pack._store(data)
	data.seek(0)
	pack = ZipPackage.from_stream(data)


def test_as_stream():
	"Get a package as a readable stream"
	stream = ZipPackage().as_stream()
	assert hasattr(stream, 'read')


def test_create_and_open(writable_filename):
	test_save(writable_filename)
	pack = ZipPackage.from_file(writable_filename)
	assert '/test/part.xml' in pack
	part = pack['/test/part.xml']
	assert part.data == '<test>hi there</test>'.encode('ascii')
	rendered_children = io.StringIO()
	out = six.text_type(pack.relationships.children)
	print(out, file=rendered_children)
	relations = pack.related('http://polimetrix.com/relationships/test')
	assert len(relations) == 1
	assert relations[0] == part


def test_nested_content_loads():
	"""
	Around 26:9448f50260f2, it was found that some content was not being
	loaded from sample documents.
	This test replicates that error.
	"""
	package = ZipPackage()
	main = SamplePart(package, '/test/main.xml')
	package[main.name] = main
	package.content_types.add_override(main)
	package.relate(main)
	main.data = '<test>this is the main module</test>'
	sub = SamplePart(package, '/test/sub.xml')
	package[sub.name] = sub
	package.content_types.add_override(sub)
	main.relate(sub)
	sub.data = '<test>this is the sub module</test>'
	serialized = io.BytesIO()
	package._store(serialized)
	serialized.seek(0)
	del package, main, sub
	package = ZipPackage.from_stream(serialized)
	assert '/test/main.xml' in package
	assert package['/test/main.xml']
	sub = package['/test/sub.xml']
	assert b'sub module' in sub.data
