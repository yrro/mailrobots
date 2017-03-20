from pytest import *

aliases_text = '''\
alias: account
*: account2
account3: :fail: account should have precedence
'''

passwd_in_text = '''\
[user:account]
password = $6$CE0MQhhj0wGYjq2$jMtQd5En/oYHT7Uwbeb/IGuf1K9iWKIAUhHAIXVcwXJifC7gxT4al0BU0UE3aKtUiFXlYkC7cNW2ypohRmfz0.

[user:account2]
password = $6$CE0MQhhj0wGYjq2$jMtQd5En/oYHT7Uwbeb/IGuf1K9iWKIAUhHAIXVcwXJifC7gxT4al0BU0UE3aKtUiFXlYkC7cNW2ypohRmfz0.

[user:account3]
password = $6$CE0MQhhj0wGYjq2$jMtQd5En/oYHT7Uwbeb/IGuf1K9iWKIAUhHAIXVcwXJifC7gxT4al0BU0UE3aKtUiFXlYkC7cNW2ypohRmfz0.
'''

def test_alias_delivery(sendmail, imap, print_logs, print_journal):
    try:
        sendmail(To='alias@test.example', Subject='non-fallback test')
        imap.select()
        assert ('OK', [b'1']) == imap.uid('search', 'subject "fallback test"')
    finally:
        print_logs()
        print_journal()

@mark.parametrize('imap_account', ['account2@test.example'])
def test_fallback_delivery(sendmail, imap, print_logs, print_journal):
    try:
        sendmail(To='nonexisting@test.example', Subject='fallback test')
        imap.select()
        assert ('OK', [b'1']) == imap.uid('search', 'subject "fallback test"')
    finally:
        print_logs()
        print_journal()

@mark.parametrize('imap_account', ['account3@test.example'])
def test_account_overrides_alias(sendmail, imap, print_logs, print_journal):
    try:
        sendmail(To='account3@test.example', Subject='should be in mailbox')
        imap.select()
        assert ('OK', [b'1']) == imap.uid('search','subject "should be in mailbox"')
    finally:
        print_logs()
        print_journal()
