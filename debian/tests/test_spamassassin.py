import email
import smtplib

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
