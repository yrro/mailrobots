import os
import subprocess

from pytest import *

@mark.parametrize('dummy_address', [
    '216.58.201.46',
    '2a00:1450:4009:80f::200e',
])
def test_asn(sendmail, imap, print_logs, print_journal):
    try:
        sendmail(To='account@test.example', Subject='asn test', headers={'X-Sender-ASN': 'remove me'})
        imap.select()
        status, uids = imap.uid('search', 'subject "asn test"')
        assert status == 'OK'
        status, x = imap.uid('fetch', uids[0].split()[0], '(body[header.fields (x-sender-asn)])')
        assert status == 'OK'
        assert b'X-Sender-ASN: AS15169 Google Inc.\r\n\r\n' == x[0][1]
    finally:
        print_logs()
        print_journal()

@mark.xfail(reason="some kind of resolved race with the updating of /etc/hosts")
@mark.parametrize('dummy_address', [
    '216.58.201.46',
    '2a00:1450:4009:80f::200e',
])
def test_public_suffix(sendmail, imap, print_logs, print_journal):
    try:
        sendmail(To='account@test.example', Subject='public suffix test', headers={'X-Sender-Public-Suffix': 'remove me'})
        imap.select()
        status, uids = imap.uid('search', 'subject "public suffix test"')
        assert status == 'OK'
        status, x = imap.uid('fetch', uids[0].split()[0], '(body[header.fields (x-sender-public-suffix)])')
        assert status == 'OK'
        assert b'X-Sender-Public-Suffix: 1e100.net\r\n\r\n' == x[0][1]
    finally:
        print_logs()
        print_journal()

@mark.usefixtures('user_mailbox')
@mark.parametrize('address', ['216.58.201.46', '2a00:1450:4009:80f::200e'])
def test_public_suffix_bh(address):
    with subprocess.Popen(['/usr/sbin/exim', '-bh', address], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
        o, e = p.communicate('''EHLO sam\nMAIL FROM:<>\nRCPT TO:<account@test.example>\nDATA\nSubject: blah\n\nbody\n.\nQUIT\n'''.encode('ascii'))
    assert b'X-Sender-Public-Suffix: 1e100.net' in e

def test_public_suffix_update():
    subprocess.check_call(['systemctl', 'start', 'mailrobots-publicsuffix-update.service'])
    assert os.path.exists('/var/lib/mailrobots/publicsuffix/public_suffix_list.dat')
