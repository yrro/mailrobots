import imaplib

from pytest import *

def test_plain_logindisabled_capabilities(imap_preauth):
    assert 'LOGINDISABLED' in imap_preauth.capabilities

def test_plain_login_privacy_required(imap_preauth):
    with raises(imaplib.IMAP4.error) as excinfo:
        imap_preauth.login('account@test.example', 'password')
    assert excinfo.value.args[0].startswith(b'[PRIVACYREQUIRED]')

@mark.usefixtures('user_mailbox')
def test_tls_login(imap_preauth):
    imap_preauth.starttls()
    imap_preauth.login('account@test.example', 'password')
