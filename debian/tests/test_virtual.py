import smtplib
import subprocess

from pytest import *

aliases_text = '''\
alias:     account
defer:     :defer: temporary failure
fail:      :fail: permanent failure
blackhole: :blackhole: drop message
file:      /should-be-forbidden
filter:    # Exim filter
pipe:      |should-be-forbidden
'''

@mark.parametrize('address', [
    'alias',
    'account',
    'account-foo',
    'account+foo',
])
def test_delivery(address, sendmail, imap, print_logs, print_journal):
    try:
        sendmail(To=address+'@test.example', Subject=address+' test')
        imap.select()
        assert ('OK', [b'1']) == imap.uid('search', 'subject "{} test"'.format(address))
    finally:
        print_logs()
        print_journal()

@mark.parametrize('address,logmessage', [
    ('blackhole', ' => :blackhole: <blackhole@test.example> R=virtual_alias\n'),
    ('file', ' R=virtual_alias: delivery to file forbidden\n'),
    ('pipe', ' R=virtual_alias: delivery to pipe forbidden\n'),
])
def test_special_aliases_accept(address, logmessage, sendmail, imap, print_logs, print_journal):
    try:
        sendmail(To=address+'@test.example')
        imap.select()
        assert ('OK', [b'']) == imap.uid('search', 'ALL')
        with open('/var/log/exim4/mainlog') as m:
            assert any(line for line in m if line.endswith(logmessage))
    finally:
        print_logs()
        print_journal()

@mark.parametrize('address,code', [
    ('defer',       451),
    ('fail',        550),
    ('filter',      451),
    ('nonexistent', 550),
])
def test_special_aliases_reject(address, code, sendmail, print_logs, print_journal):
    try:
        with raises(smtplib.SMTPRecipientsRefused) as excinfo:
            sendmail(To=address+'@test.example')
        assert code == excinfo.value.recipients[address+'@test.example'][0]
    finally:
        print_logs()
        print_journal()

@mark.xfail(reason="haven't got this working yet", strict=True)
@mark.parametrize('separator', ['+', '-'])
def test_save_to_detail_mailbox(imap, sendmail, print_logs, print_journal, separator):
    try:
        imap.create('detail')
        sendmail(To='account{}detail@test.example'.format(separator), Subject='deliver to detail mailbox')
        imap.select('detail')
        assert ('OK', [b'1']) == imap.uid('search', 'subject "deliver to detail mailbox"')
    finally:
        print_logs()
        print_journal()
