CrossCompute
============
Publish your computational model.

Please see http://crosscompute.com/docs for tutorials and examples.


Install
-------
::

    pip install -U crosscompute
    pip install -U crosscompute-integer
    pip install -U crosscompute-text
    pip install -U crosscompute-image
    pip install -U crosscompute-table
    pip install -U crosscompute-geotable


Use
---
::

    git clone https://github.com/crosscompute/crosscompute-examples
    crosscompute run find-prime-factors
    crosscompute serve find-prime-factors --host 0.0.0.0


Credits
-------
The concept for this application framework grew from specifications drafted in NSF SBIR Proposal #7589589, which was not funded, but we built it regardless because we believed in it.

Thanks to our project manager `Jennifer Ruda <https://github.com/jenniferrrr>`_ for reviewing the initial specifications and supporting the overall development process. Thanks to `Salah Ahmed <https://github.com/salah93>`_ for testing our framework on Mac OS X and to `Aida Shoydokova <https://github.com/AShoydokova>`_ for testing our framework on Windows.
