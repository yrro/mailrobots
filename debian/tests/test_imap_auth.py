import imaplib

from pytest import *

def test_plain_logindisabled_capabilities(imap_preauth, print_journal):
    try:
        assert 'LOGINDISABLED' in imap_preauth.capabilities
    finally:
        print_journal()

def test_plain_login_privacy_required(imap_preauth, print_journal):
    try:
        with raises(imaplib.IMAP4.error) as excinfo:
            imap_preauth.login('account@test.example', 'password')
        assert excinfo.value.args[0].startswith(b'[PRIVACYREQUIRED]')
    finally:
        print_journal()

@mark.usefixtures('user_mailbox')
def test_tls_login(imap_preauth, print_journal):
    try:
        imap_preauth.starttls()
        imap_preauth.login('account@test.example', 'password')
    finally:
        print_journal()
