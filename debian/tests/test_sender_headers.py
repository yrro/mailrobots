import os
import subprocess

from pytest import *

@mark.usefixtures('user_mailbox')
@mark.parametrize('address', ['216.58.201.46', '2a00:1450:4009:80f::200e'])
def test_sender_asn(address):
    with subprocess.Popen(['/usr/sbin/exim', '-bh', address], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
        o, e = p.communicate('''EHLO sam\nMAIL FROM:<>\nRCPT TO:<account@test.example>\nDATA\nSubject: blah\n\nbody\n.\nQUIT\n'''.encode('ascii'))
    assert b'X-Sender-ASN: AS15169 Google Inc.' in e

@mark.usefixtures('user_mailbox')
@mark.parametrize('address', ['216.58.201.46', '2a00:1450:4009:80f::200e'])
def test_sender_public_suffix(address):
    with subprocess.Popen(['/usr/sbin/exim', '-bh', address], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
        o, e = p.communicate('''EHLO sam\nMAIL FROM:<>\nRCPT TO:<account@test.example>\nDATA\nSubject: blah\n\nbody\n.\nQUIT\n'''.encode('ascii'))
    assert b'X-Sender-Public-Suffix: 1e100.net' in e

def test_public_suffix_update():
    subprocess.check_call(['systemctl', 'start', 'mailrobots-publicsuffix-update.service'])
    assert os.path.exists('/var/lib/mailrobots/publicsuffix/public_suffix_list.dat')
