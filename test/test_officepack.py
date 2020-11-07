import pkg_resources

import pytest

from openpack.officepack import OfficePackage


@pytest.fixture
def officepack_sample(request):
    return pkg_resources.resource_stream(__name__, 'empty.docx')


def test_open(officepack_sample):
    OfficePackage.from_stream(officepack_sample)


def test_start_part(officepack_sample):
    doc = OfficePackage.from_stream(officepack_sample)
    assert doc.start_part
