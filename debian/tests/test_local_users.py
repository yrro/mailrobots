import subprocess

from pytest import *

def test_system_user():
    with subprocess.Popen(['exim', '-bt', 'daemon'], stderr=subprocess.PIPE) as p:
        o, e, = p.communicate()
    lines = e.split(b'\n')
    i, line = next(((i, line) for i, line in enumerate(lines) if line.startswith(b'R: system_user for daemon@')), (None, None))
    assert i
    assert lines[i+1].startswith(b'R: system_aliases for root@')

@mark.usefixtures('local_user')
def test_local_user():
    with subprocess.Popen(['exim', '-bt', 'localuser'], stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
        o, e = p.communicate()
    olines = o.split(b'\n')
    elines = e.split(b'\n')
    assert olines[-2].endswith(b' is undeliverable: local user has no forwarding address')
    assert elines[-2].startswith(b'R: no_local_mail for localuser@')
