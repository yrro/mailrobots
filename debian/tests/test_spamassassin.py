import email
import os
import smtplib
import shutil
import subprocess

from pytest import *

@mark.xfail(reason='needs virtual alias rework', strict=True)
def test_spamd_receives_no_mail(sendmail, print_logs, print_journal):
    try:
        with raises(smtplib.SMTPRecipientsRefused) as excinfo:
            sendmail(To='spamd@spamd.invalid', Subject='spamd reject test')
        assert (550, 'Mail not accepted at this address') == excinfo.value.args[1]
    finally:
        print_logs()
        print_journal()

def test_obvious_spam_rejected(sendmail, print_logs, print_journal):
    try:
        with raises(smtplib.SMTPDataError) as excinfo:
            sendmail(To='account@test.example', Subject='spamassassin test', body='Spam message, should be blocked\r\nXJS*C4JDBQADN1.NSBN3*2IDNEN*GTUBE-STANDARD-ANTI-UBE-TEST-EMAIL*C.34X\r\n')
        assert 550 == excinfo.value.args[0]
        assert b'Message classified as spam' in excinfo.value.args[1]
    finally:
        print_logs()
        print_journal()

@mark.xfail(strict=True)
def test_large_messages_not_scanned(sendmail, print_logs, print_journal):
    try:
        assert 0
    finally:
        print_logs()
        print_journal()

@mark.parametrize('header', [
    'x-spam-checker-version',
    'x-spam-level',
    'x-spam-status',
    'x-spam-report',
    'x-spam-asn',
])
def test_spam_headers_added(sendmail, imap, print_logs, print_journal, header):
    try:
        sendmail(To='account@test.example', Subject='spam header test', headers={header: 'should be removed'})
        imap.select()
        status, uids = imap.uid('search', 'subject "spam header test"')
        assert 'OK' == status
        status, resp = imap.uid('fetch', uids[0].split()[0], '(rfc822)')
        assert 'OK' == status
        msg = email.message_from_bytes(resp[0][1])
        assert 1 == len(msg.get_all(header))
        assert 'should be removed' != msg[header]
    finally:
        print_logs()
        print_journal()

def test_spam_delivered_to_spam_mailbox(lsendmail, imap, print_logs, print_journal):
    try:
        lsendmail(To='account@test.example', Subject='spam sieve test', headers={'X-Spam-Status': 'score=8.0 required=5.0'})
        status, dat = imap.select('Spam')
        assert 'OK' == status
        status, uids = imap.uid('search', 'subject "spam sieve test"')
        assert ('OK', [b'1']) == imap.uid('search', 'subject "spam sieve test"')
        status, resp = imap.uid('fetch', uids[0].split()[0], '(flags)')
        assert 'OK' == status
        assert b'1 (UID 1 FLAGS (\\Recent Junk $Junk))' == resp[0]
    finally:
        print_logs()
        print_journal()

@yield_fixture
def mock_spamc_learn():
    try:
        subprocess.check_call(['dpkg-divert', '--local', '--rename', '--add', '/usr/lib/mailrobots/sieve-pipe/spamc-learn'])
        with open('/usr/lib/mailrobots/sieve-pipe/spamc-learn', 'w') as f:
            f.write(
                  '#!/bin/bash\n'
                  'echo USER="$USER" >>/spamc-learn/output\n'
                  'echo @="$@" >>/spamc-learn/output\n'
            )
        os.chmod('/usr/lib/mailrobots/sieve-pipe/spamc-learn', 0o755)
        os.mkdir('/spamc-learn')
        shutil.chown('/spamc-learn', 'mailstorage', 'mailstorage')
        yield '/spamc-learn/output'
    finally:
        if os.path.exists('/spamc-learn'):
            shutil.rmtree('/spamc-learn')
        os.remove('/usr/lib/mailrobots/sieve-pipe/spamc-learn')
        subprocess.check_call(['dpkg-divert', '--rename', '--remove', '/usr/lib/mailrobots/sieve-pipe/spamc-learn'])

@mark.parametrize('verb', ['COPY', 'MOVE'])
def test_tell_spam(lsendmail, imap, verb, print_logs, print_journal, mock_spamc_learn):
    try:
        lsendmail(To='account@test.example', Subject='spam tell test', headers={'X-Spam-Status': 'score=1.0 required=5.0'})
        status, dat = imap.select('INBOX')
        assert 'OK' == status
        status, uids = imap.uid('search', 'subject "spam tell test"')
        assert 'OK' == status
        status, resp = imap.uid(verb, uids[0].split()[0], 'Spam')
        assert 'OK' == status
        status, dat = imap.select('Spam')
        assert 'OK' == status
        assert ('OK', [b'1']) == imap.uid('search', 'subject "spam tell test"')
        with open(mock_spamc_learn) as f:
            assert ['USER=account@test.example\n', '@=spam\n'] == f.readlines()
    finally:
        print_logs()
        print_journal()

@mark.parametrize('verb', ['COPY', 'MOVE'])
def test_tell_ham(lsendmail, imap, verb, print_logs, print_journal, mock_spamc_learn):
    try:
        lsendmail(To='account@test.example', Subject='ham tell test', headers={'X-Spam-Status': 'score=8.0 required=5.0'})
        status, dat = imap.select('Spam')
        assert 'OK' == status
        status, uids = imap.uid('search', 'subject "ham tell test"')
        assert 'OK' == status
        status, resp = imap.uid(verb, uids[0].split()[0], 'INBOX')
        status, dat = imap.select('INBOX')
        assert 'OK' == status
        assert ('OK', [b'1']) == imap.uid('search', 'subject "ham tell test"')
        with open(mock_spamc_learn) as f:
            assert ['USER=account@test.example\n', '@=ham\n'] == f.readlines()
    finally:
        print_logs()
        print_journal()

@mark.parametrize('verb', ['COPY', 'MOVE'])
def test_trash_spam_no_tell(lsendmail, imap, verb, print_logs, print_journal, mock_spamc_learn):
    try:
        lsendmail(To='account@test.example', Subject='spam trash test', headers={'X-Spam-Status': 'score=8.0 required=5.0'})
        status, dat = imap.create('Trash')
        assert 'OK' == status
        status, dat = imap.select('Spam')
        assert 'OK' == status
        status, uids = imap.uid('search', 'subject "spam trash test"')
        assert 'OK' == status
        status, resp = imap.uid(verb, uids[0].split()[0], 'Trash')
        assert 'OK' == status
        status, dat = imap.select('Trash')
        assert 'OK' == status
        assert ('OK', [b'1']) == imap.uid('search', 'subject "spam trash test"')
        assert not os.path.exists(mock_spamc_learn)
    finally:
        print_logs()
        print_journal()
