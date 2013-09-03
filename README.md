kernel-package
==============

Make RPMs from upstream kernel easy.

Requirements
------------

* python
* rpmbuild
* mock
* git

How to use
----------

1. Clone Linus git tree
2. Change dir to clonned repo
3. (OPTIONAL) Put custom config-local, patches to sources/ directory
4. Start utility
5. Make RPMs
6. Install RPMs


```
$ git clone git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git linux
$ cd linux
$ /path/to/kernel-package.py
$ mock -r fedora-19-x86_64 --rebuild sources/*.src.rpm --resultdir sources/rpms
# yum install sources/rpms/*.rpm
```

TODO
----

* Support linux-stable git tree
