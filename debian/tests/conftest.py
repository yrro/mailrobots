import email.message
import imaplib
import os
import pwd
import shutil
import smtplib
import socket
import subprocess
import time

from pytest import *

imaplib.Debug=4

logs = [
    '/var/mail/mail',
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
def user_mailbox(request):
    os.mkdir('/srv/mail/domains/test.example', mode=0o700)

    aliases = open('/srv/mail/domains/test.example/aliases', 'w')
    aliases.write(request.module.aliases_text)
    aliases.close()

    passwd_in = open('/srv/mail/domains/test.example/passwd.in', 'w')
    passwd_in.write(request.module.passwd_in_text)
    passwd_in.close()

    subprocess.check_call(['/usr/lib/mailrobots/build'], cwd='/srv/mail')
    subprocess.check_call(['/usr/lib/mailrobots/permissions'], cwd='/srv/mail')

    yield

    if os.path.exists('/srv/mail/domains/test.example'):
        shutil.rmtree('/srv/mail/domains/test.example')
    if os.path.exists('/srv/mail/passwd'):
        os.remove('/srv/mail/passwd')

@yield_fixture
def imap(user_mailbox): # XXX use usesfixtures
    imap = imaplib.IMAP4('localhost')
    imap.login('account@test.example', 'password')
    yield imap
    try:
        imap.logout()
    except Exception:
        pass

@yield_fixture
def smtp(user_mailbox): # XXX use usesfixtures
    smtp = smtplib.SMTP('localhost', 25)
    #smtp.set_debuglevel(1)
    yield smtp
    try:
        smtp.quit()
    except Exception:
        pass

@yield_fixture
def sendmail(smtp):
    def f(body='test message', Sender=pwd.getpwuid(os.getuid()).pw_name + '@' + socket.gethostname(), **kwargs):
        msg = email.message.Message()
        msg['Sender'] = Sender
        for k, v in kwargs.items():
            msg[k] = v
        msg.set_payload(body)
        r = smtp.send_message(msg)
        time.sleep(0.25)
        return r
    yield f
