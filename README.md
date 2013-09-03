kernel-package
==============

Make RPMs from upstream kernel easy.

Requirements
------------

* python for run kernel-package
* rpmbuild for make src.rpm
* mock for make rpms from src.rpm
* git for get upstream Linus sources

How to use
----------

1. Clone Linus git tree
2. Change dir to clonned repo
3. (OPTIONAL) Put custom config-local, patches to sources/ directory
4. Start utility
5. Make RPMs
6. Install RPMs


```
$ git clone git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
$ cd linux
$ /path/to/kernel-package.py
$ mock -r fedora-19-x86_64 --rebuild sources/*.src.rpm --resultdir sources/rpms
# yum install sources/rpms/*.rpm
```

Options
-------

Use /path/to/kernel-package.py -h for get help about options

Known issues
----

* Support linux-stable git tree. I don't like to support.
