from .zippack import ZipPackage


class OfficePackage(ZipPackage):
	"""
	A Microsoft Office OOXML package.
	"""

	main_rel = (
		"http://schemas.openxmlformats.org"
		"/officeDocument/2006/relationships/officeDocument"
	)

	@property
	def start_part(self):
		return self.related(self.main_rel)[0]
