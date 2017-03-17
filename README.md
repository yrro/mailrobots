robots.org.uk mail system
=========================

Goal: a deb which depends on all necessary packages, and ships all necessary
config files.

autopkgtest to drive a test suite.

autopkgtest testbed
-------------------

Until [autopkgtest gains support for systemd-nspawn](https://bugs.debian.org/809443),
LXC looks like the next best thing.

    $ lxc-create -B dir -n mailrobots -t "$PWD/debian2"
