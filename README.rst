.. image:: https://img.shields.io/pypi/v/openpack.svg
   :target: https://pypi.org/project/openpack

.. image:: https://img.shields.io/pypi/pyversions/openpack.svg

.. image:: https://github.com/jaraco/openpack/actions/workflows/main.yml/badge.svg
   :target: https://github.com/jaraco/openpack/actions?query=workflow%3A%22tests%22
   :alt: tests

.. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
    :target: https://github.com/astral-sh/ruff
    :alt: Ruff

.. .. image:: https://readthedocs.org/projects/PROJECT_RTD/badge/?version=latest
..    :target: https://PROJECT_RTD.readthedocs.io/en/latest/?badge=latest

.. image:: https://img.shields.io/badge/skeleton-2025-informational
   :target: https://blog.jaraco.com/skeleton

``openpack`` provides base functionality for working with the `Open
Office XML (OOXML) <https://en.wikipedia.org/wiki/Office_Open_XML>`_
format in Python.

Introduction
============

Openpack is a base library for OpenXML documents. It is used by the `paradocx
<https://pypi.org/project/paradocx>`_ and `XlsXcessive
<https://pypi.org/project/xlsxcessive>`_.

Utilities
=========

Openpack includes two utilities for working with OpenXML documents from the
command-line, `part-edit` and `zip-listdir`.

These commands are additionally exposed as modules and may be invoked
using ``python -m``, e.g. ``python -m openpack.part-edit``.

zip-listdir
-----------

``zip-listdir`` isn't specific to OpenXML, and will work on any zip file.
Since OpenXML documents are themselves zip files, however, it is useful to have
when working with OpenXML::

    > zip-listdir ../paradocx/data.docx
      [Content_Types].xml
    d _rels
    d word

``zip-listdir`` lists the files and directories and can be used to list
sub-directories as well::

    > zip-listdir ../paradocx/data.docx/word
    d _rels
      document.xml

part-edit
---------

While ``zip-listdir`` enables inspecting the structure of the zip content of
an OpenXML document, ``part-edit`` facilitates editing the various parts of
those documents using the client's text editor. For example, to edit the
``word/document.xml`` as found in data.docx from the previous example, simply
invoke part-edit::

    > part-edit ../paradocx/data.docx/word/document.xml

The program will attempt to use the default text editor to edit the file. If
the default editor is not sufficient, the user may specify an editor by
setting either XML_EDITOR or EDITOR environment variables.

``part-edit`` will parse the zip file, locate the content within the zip file,
extract that content to a temporary file, and then open that content in an
editor. After the editor is closed, if the file was changed, the zip file
will be updated with the new content.

The user may pass the optional ``--reformat-xml``, in which case the XML will
be pretty-formatted for easier human readability.
