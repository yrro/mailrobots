import contextlib
import email.message
import functools
import imaplib
import os
import pwd
import shutil
#import sievelib.managesieve
import smtplib
import socket
import subprocess
import time

from pytest import *

imaplib.Debug=4

if 'MOVE' not in imaplib.Commands:
    imaplib.Commands['MOVE'] = imaplib.Commands['COPY']

logs = [
    '/var/log/exim4/mainlog',
    '/var/log/exim4/rejectlog',
    '/var/log/exim4/paniclog',
]

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
        for line in open(path):
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
            print('-- Logs end. --')
    yield f

passwd_in_text = '''\
[user:account]
password = $6$CE0MQhhj0wGYjq2$jMtQd5En/oYHT7Uwbeb/IGuf1K9iWKIAUhHAIXVcwXJifC7gxT4al0BU0UE3aKtUiFXlYkC7cNW2ypohRmfz0.
quota = 100KB
'''

@yield_fixture
def user_mailbox(request):
    try:
        os.mkdir('/srv/mail/domains/test.example', mode=0o700)

        aliases = open('/srv/mail/domains/test.example/aliases', 'w')
        aliases.write(getattr(request.module, 'aliases_text', ''))
        aliases.close()

        passwd_in = open('/srv/mail/domains/test.example/passwd.in', 'w')
        passwd_in.write(getattr(request.module, 'passwd_in_text', passwd_in_text))
        passwd_in.close()

        subprocess.check_call(['/usr/lib/mailrobots/build'], cwd='/srv/mail')
        subprocess.check_call(['/usr/lib/mailrobots/permissions'], cwd='/srv/mail')

        yield

    finally:
        if os.path.exists('/srv/mail/domains/test.example'):
            shutil.rmtree('/srv/mail/domains/test.example')
        if os.path.exists('/srv/mail/passwd'):
            os.remove('/srv/mail/passwd')

@fixture
def imap_account():
    return 'account@test.example'

@yield_fixture
def imap_preauth():
    # Dovecot treats connections with the same source & destination addresses
    # as trusted and does not require authentication to take place over a
    # secure channel.
    class IMAP(imaplib.IMAP4):
        def _create_socket(self):
            return socket.create_connection((self.host, self.port), source_address=('127.0.0.1', 0))
    imap = IMAP(socket.gethostname())
    yield imap
    imap.logout()

@yield_fixture
def imap(imap_preauth, imap_account, user_mailbox):
    imap_preauth.starttls()
    imap_preauth.login(imap_account, 'password')
    yield imap_preauth

@fixture
def smtp_port():
    return 25

@yield_fixture
def smtp(smtp_port, user_mailbox):
    smtp = smtplib.SMTP()
    #smtp.set_debuglevel(1)
    # If we connect to localhost then the connection to the SMTP server uses
    # ::1 (or 127.0.0.1) as its source address, which is in +relay_from_hosts.
    # This is problematic because Exim will accept messages without verifying
    # whether they can be delivered. Using a different address will guarantee
    # that Exim will refuse to accept mail that it can't deliver.
    smtp.connect(socket.gethostname(), smtp_port)
    try:
        yield smtp
    finally:
        smtp.quit()

@yield_fixture
def lmtp(user_mailbox):
    lmtp = smtplib.LMTP()
    lmtp.set_debuglevel(1)
    lmtp.connect('/run/dovecot/lmtp')
    try:
        yield lmtp
    finally:
        lmtp.quit()

def _send_message(smtp, body='test message\r\n', Sender=pwd.getpwuid(os.getuid()).pw_name + '@' + socket.gethostname(), headers={}, **kwargs):
    msg = email.message.Message()
    msg['Sender'] = Sender
    for k, v in kwargs.items():
        msg[k] = v
    for k, v in headers.items():
        msg[k] = v
    msg.set_payload(body)
    r = smtp.send_message(msg)
    time.sleep(0.25)
    return r

@yield_fixture
def sendmail(smtp):
    yield functools.partial(_send_message, smtp)

@yield_fixture
def lsendmail(lmtp):
    yield functools.partial(_send_message, lmtp)

@yield_fixture
def local_user():
    subprocess.check_call(['adduser', '--disabled-password', '--gecos', 'mailrobots test user', 'localuser'])
    yield
    subprocess.check_call(['deluser', '--remove-home','localuser'])

@yield_fixture
def managesieve(user_mailbox):
    #c = sievelib.managesieve.Client(socket.gethostname())
    #c.connect('account@test.example', 'password')
    #yield c
    #c.logout()
    class Client:
        def putscript(self, name, script):
            os.makedirs('/srv/mail/domains/test.example/users/account/sieve')
            with open('/srv/mail/domains/test.example/users/account/sieve/{}.sieve'.format(name), 'w') as f:
                f.write(script)
            subprocess.check_call(['chown', '-R', 'mailstorage:mailstorage', '/srv/mail/domains/test.example/users/account/sieve'])

        def setactive(self, name):
            os.symlink('sieve/{}.sieve'.format(name), '/srv/mail/domains/test.example/users/account/.dovecot.sieve')
    yield Client()
    try:
        os.remove('/srv/mail/domains/test.example/users/account/.dovecot.sieve')
    except FileNotFoundError:
        pass
    if os.path.exists('/srv/mail/domains/test.example/users/account/sieve'):
        shutil.rmtree('/srv/mail/domains/test.example/users/account/sieve')
