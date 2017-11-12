import re


def validator(f, etype=ValueError):
	def _validate(*args, **params):
		try:
			return f(*args, **params)
		except AssertionError as e:
			raise etype(*e.args)
	return _validate


_nstag = re.compile('(\{http://[^}]+\}){0,1}([a-zA-Z0-9_]+)')


def parse_tag(t):
	return _nstag.match(t).groups()


def get_ext(name):
	"""
	Return the extension only for a name (like a filename)

	>>> get_ext('foo.bar')
	'bar'
	>>> get_ext('.only')
	'only'
	>>> get_ext('')
	''
	>>> get_ext('noext')
	''
	>>> get_ext('emptyext.')
	''

	Note that for any non-empty string, the result will never be the
	same as the input. This is a useful property for basepack.
	"""
	other, sep, ext = name.partition('.')
	return ext
