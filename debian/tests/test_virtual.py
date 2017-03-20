import email.message
import functools
import imaplib
import os
import shutil
import smtplib
import socket
import subprocess
import sys
import time

from pytest import *

imaplib.Debug=4

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

logs = [
    '/var/mail/mail',
    '/var/log/exim4/mainlog',
    '/var/log/exim4/rejectlog',
    '/var/log/exim4/paniclog',
]

def sendmail(smtp, body='test message', Sender='nobody@' + socket.gethostname(), **kwargs):
    msg = email.message.Message()
    msg['Sender'] = Sender
    for k, v in kwargs.items():
        msg[k] = v
    msg.set_payload(body)
    smtp.send_message(msg)

@yield_fixture
def print_logs():
    for log in logs:
        if os.path.exists(log):
            os.remove(log)
    def f():
        for log in logs:
            print_file(log)
    yield f

@yield_fixture
def print_file(path):
    print(' ╭┤', path, sep='')
    try:
        for line in open(path).readlines():
            print(' │', line, end='')
    except OSError as e:
        print(' ╰┄', e, sep='')
    else:
        print(' ╰┄')

@yield_fixture
def print_journal():
    with subprocess.Popen(['journalctl', '-n', '0', '--show-cursor'], stdout=subprocess.PIPE) as p:
        o, e = p.communicate()
    cursor = None
    for line in o.split(b'\n'):
        before, sep, after = line.partition(b'-- cursor: ')
        if sep != b'':
            cursor = after.decode('ascii')
            break
    def f():
        if cursor is not None:
            with subprocess.Popen(['journalctl', '--no-hostname', '--after-cursor=' + cursor]) as p:
                p.wait()
    yield f

@yield_fixture
def user_mailbox():
    os.mkdir('/srv/mail/domains/test.example', mode=0o700)

    aliases = open('/srv/mail/domains/test.example/aliases', 'w')
    aliases.write(aliases_text)
    aliases.close()

    passwd_in = open('/srv/mail/domains/test.example/passwd.in', 'w')
    passwd_in.write(passwd_in_text)
    passwd_in.close()

    subprocess.check_call(['/usr/lib/mailrobots/build'], cwd='/srv/mail')
    subprocess.check_call(['/usr/lib/mailrobots/permissions'], cwd='/srv/mail')

    smtp = smtplib.SMTP('localhost', 25)
    smtp.set_debuglevel(1)
    imap = imaplib.IMAP4('localhost')
    imap.login('account@test.example', 'password')
    yield smtp, imap

    try:
        smtp.quit()
    except Exception:
        pass

    try:
        imap.logout()
    except Exception:
        pass

    if os.path.exists('/srv/mail/domains/test.example'):
        shutil.rmtree('/srv/mail/domains/test.example')
    if os.path.exists('/srv/mail/passwd'):
        os.remove('/srv/mail/passwd')

@mark.parametrize('address', [
    'alias',
    'pattern12345',
    'account',
    'account-foo', # XXX wtf
    'account+foo',
])
def test_delivery(address, user_mailbox, print_logs, print_journal):
    smtp, imap = user_mailbox
    sendmail(smtp, To=address+'@test.example', Subject=address+' test')
    time.sleep(0.25)
    imap.select()
    print_logs()
    print_journal()
    assert ('OK', [b'1']) == imap.uid('search', 'subject "{} test"'.format(address))

@mark.parametrize('address,expected', [
    ('defer',     b'cannot be resolved at this time: temporary failure'),
    ('fail',      b'undeliverable: permanent failure'),
    ('blackhole', b'is discarded'),
    ('file',      b'file_transport unset in virtual_alias router'),
    ('filter',    b'filtering not enabled'),
    ('pipe',      b'pipe_transport unset in virtual_alias router'),
])
def test_special_aliases(address, expected, user_mailbox, print_journal):
    with subprocess.Popen(['exim', '-bt', address+'@test.example'], stdout=subprocess.PIPE) as p:
        o, e = p.communicate()
    print_logs()
    print_journal()
    assert expected in o

def test_save_to_detail_mailbox(user_mailbox, print_logs, print_journal):
    smtp, imap = user_mailbox
    imap.create('detail')
    sendmail(smtp, To='account+detail@test.example', Subject='deliver to detail mailbox')
    time.sleep(0.25)
    imap.select('detail')
    print_logs()
    print_journal()
    assert ('OK', [b'1']) == imap.uid('search', 'subject "deliver to detail mailbox"')
