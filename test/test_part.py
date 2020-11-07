import pytest

from openpack.basepack import Package, Part


class TestParts:
    def setup_class(cls):
        cls.package = Package()

    def test_create(self):
        self.part = Part(self.package, '/something.html', content_type='text/html')

    def test_bad_names(self):
        with pytest.raises(ValueError):
            Part(self.package, 'something')
