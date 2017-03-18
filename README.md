robots.org.uk mail system
=========================

Goal: a deb which depends on all necessary packages, and ships all necessary
config files.

autopkgtest to drive a test suite.

autopkgtest testbed
-------------------

Until [autopkgtest gains support for systemd-nspawn](https://bugs.debian.org/809443),
LXC looks like the next best thing.

Create the testbed:

    $ (cd debian/tests/testbed && lxc-create -B dir -n mailrobots -f lxc.conf -t "$PWD/debian2"
