kernel-package
==============

Make RPMs from upstream kernel easy.

How to use
----------

1. Clone Linus git tree
2. Change dir to clonned repo
3. Start making sources
4. Setup rpmbuild tree
5. Move sources to rpmbuild tree
6. Make RPMs


```
$ git clone git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git linux
$ cd linux
$ /path/to/kernel-package.py
$ rpmdev-setuptree
$ mv sources/kernel.spec ~/rpmbuild/SPECS/
$ mv sources/* ~/rpmbuild/SOURCES/
# yum-builddep ~/rpmbuild/SPECS/kernel.spec
$ rpmbuild -ba ~/rpmbuild/SPECS/kernel.spc
```

TODO
----

1. Automation make srpm, rpm
2. Support linux-stable git tree
3. Support automatically add user-patches from sources/ directory
