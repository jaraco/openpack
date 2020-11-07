"""
To save to a stream:

>>> from openpack.zippack import ZipPackage
>>> zp = ZipPackage()
>>> import io
>>> f = io.BytesIO()
>>> zp.save(f)
>>> from zipfile import ZipFile
>>> zf = ZipFile(f)
>>> zf.namelist()
['[Content_Types].xml', '_rels/.rels']
>>> zf.read('[Content_Types].xml')
b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\
<Default ContentType="application/vnd.openxmlformats-package.relationships+xml" \
Extension="rels"/></Types>'
"""
