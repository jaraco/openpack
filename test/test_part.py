import pytest

from openpack.basepack import Package, Part


class TestParts:
    def test_create(self):
        self.part = Part(Package(), '/something.html', content_type='text/html')

    def test_bad_names(self):
        with pytest.raises(ValueError):
            Part(Package(), 'something')
