import pathlib

import pytest

from openpack.officepack import OfficePackage


@pytest.fixture
def officepack_sample(request):
    return pathlib.Path(__file__).parent.joinpath('empty.docx').open('rb')


def test_open(officepack_sample):
    OfficePackage.from_stream(officepack_sample)


def test_start_part(officepack_sample):
    doc = OfficePackage.from_stream(officepack_sample)
    assert doc.start_part
