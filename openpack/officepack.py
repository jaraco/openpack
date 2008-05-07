from zippack import ZipPackage

class OfficePackage(ZipPackage):
	"""Handles MSOffice files and correctly sets the start part."""

	main_rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"

	def open(self):
		ZipPackage.open(self)
		# set the first occurence of the officeDocument relationship as the
		# "start part" for the package
		self.start_part = self.related(self.main_rel)[0]


