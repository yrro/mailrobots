import smtplib
import subprocess

from pytest import *

aliases_text = '''\
alias:     account
^pattern:  account
defer:     :defer: temporary failure
fail:      :fail: permanent failure
blackhole: :blackhole: drop message
file:      /should-be-forbidden
filter:    # Exim filter
pipe:      |should-be-forbidden
'''

passwd_in_text = '''\
[user:account]
password = $6$CE0MQhhj0wGYjq2$jMtQd5En/oYHT7Uwbeb/IGuf1K9iWKIAUhHAIXVcwXJifC7gxT4al0BU0UE3aKtUiFXlYkC7cNW2ypohRmfz0.
quota = 100KB
'''

@mark.parametrize('address', [
    'alias',
    'pattern12345',
    'account',
    'account-foo', # XXX wtf
    'account+foo',
])
def test_delivery(address, sendmail, imap, print_logs, print_journal):
    sendmail(To=address+'@test.example', Subject=address+' test')
    imap.select()
    print_logs()
    print_journal()
    assert ('OK', [b'1']) == imap.uid('search', 'subject "{} test"'.format(address))

def test_non_existing_account(sendmail, print_logs, print_journal):
    with raises(smtplib.SMTPRecipientsRefused):
        print(sendmail(To='nonexisting@test.example'))
        print_logs()
        print_journal()

@mark.usefixtures('user_mailbox')
@mark.parametrize('address,expected', [
    ('defer',     b'cannot be resolved at this time: temporary failure'),
    ('fail',      b'undeliverable: permanent failure'),
    ('blackhole', b'is discarded'),
    ('file',      b'file_transport unset in virtual_alias router'),
    ('filter',    b'filtering not enabled'),
    ('pipe',      b'pipe_transport unset in virtual_alias router'),
])
def test_special_aliases(address, expected, print_logs, print_journal):
    with subprocess.Popen(['exim', '-bt', address+'@test.example'], stdout=subprocess.PIPE) as p:
        o, e = p.communicate()
    print_logs()
    print_journal()
    assert expected in o

@mark.xfail(reason="haven't got this working yet")
def test_save_to_detail_mailbox(imap, sendmail, print_logs, print_journal):
    imap.create('detail')
    sendmail(To='account+detail@test.example', Subject='deliver to detail mailbox')
    imap.select('detail')
    print_logs()
    print_journal()
    assert ('OK', [b'1']) == imap.uid('search', 'subject "deliver to detail mailbox"')
