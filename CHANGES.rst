2.1.1
~~~~~

Fixed module runner invocations.

2.1
~~~

Refreshed project metadata.

Added module runners for command-line utilities. One may
now invoke ``part-edit`` or ``zip-listdir`` thus:

    $ python -m openpack.part-edit
    $ python -m openpack.zip-listdir

2.0
~~~

Moved hosting to Github.

Dropped support for Python 2.6.

Tagged builds are automatically released if tests pass on
Python 3.5.

1.1.3
~~~~~

Issue #4: Fix issue with case sensitivity in ContentTypes.items.

1.1
~~~

Python 3 support.

1.0
~~~

As YouGov is adopting many of the principles of semver, and openpack is
stable for many months, we're declaring it suitable for a 1.0 release.
This release is functionally identical to 0.4.1.

0.4
~~~

In 0.4, many of the interfaces changed to better suit testing and other
applications of the package. Here are some of the most prominent changes
to the public API:

* `name` parameter was removed from package initiation.
* packages and zip packages can now be constructed from a file or from
  a stream using classmethods `from_file` or `from_stream`.
* packages now only have a filename attribute if they were loaded from
  a file or previously saved to a file.
* Packages no longer require handlers to determine which Part class to
  use when de-serializing a package. Parts are now self-registering by
  content-type. The only caveat is the requisite Part classes must be
  loaded (imported) before the Document is loaded.
