import smtplib

from pytest import *

@mark.parametrize('smtp_port', [25, 587])
def test_plain_relay_refused(sendmail, print_logs):
    try:
        with raises(smtplib.SMTPRecipientsRefused) as excinfo:
            sendmail(To='test@example.com')
        assert {'test@example.com': (550, b'relay not permitted')} == excinfo.value.recipients
    finally:
        print_logs()

@mark.parametrize('smtp_port', [25, 587])
def test_plain_auth_not_offered(smtp, print_logs):
    try:
        with raises(smtplib.SMTPException) as excinfo:
            smtp.login('user', 'password')
        assert ('SMTP AUTH extension not supported by server.',) == excinfo.value.args
    finally:
        print_logs()

@mark.parametrize('smtp_port', [25, 587])
def test_plain_auth_refused(smtp, print_logs):
    try:
        smtp.putcmd('AUTH PLAIN blah')
        assert (503, b'AUTH command used when not advertised') == smtp.getreply()
    finally:
        print_logs()

def test_starttls_auth_not_offered_25(smtp, print_logs):
    try:
        assert smtp.starttls()[0] == 220
        with raises(smtplib.SMTPException) as excinfo:
            smtp.login('user', 'password')
        assert ('SMTP AUTH extension not supported by server.',) == excinfo.value.args
    finally:
        print_logs()

@mark.parametrize('smtp_port', [587])
def test_starttls_auth_relay_permitted(smtp, sendmail, print_logs):
    try:
        assert smtp.starttls()[0] == 220
        smtp.login('account@test.example', 'password')
        sendmail(To='test@example.com')
    finally:
        print_logs()
