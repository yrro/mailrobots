import email.message
import imaplib
import os
import pwd
import shutil
import smtplib
import socket
import subprocess
import time

import pyroute2
from pyroute2.netlink.rtnl.ifaddrmsg import IFA_F_TENTATIVE
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
def imap(imap_account, user_mailbox): # XXX use usesfixtures
    imap = imaplib.IMAP4('localhost')
    imap.login(imap_account, 'password')
    yield imap
    try:
        imap.logout()
    except Exception:
        pass

@fixture
def smtp_port():
    return 25

@yield_fixture
def smtp(user_mailbox, smtp_port, dummy_address, dummy_interface): # XXX use usesfixtures
    smtp = smtplib.SMTP(source_address=(dummy_address, 0) if dummy_address else None)
    # If we connect to localhost then the connection to the SMTP server uses
    # ::1 (or 127.0.0.1) as its source address, which is in +relay_from_hosts.
    # This is problematic because Exim will accept messages without verifying
    # whether they can be delivered. Using a different address will guarantee
    # that Exim will refuse to accept mail that it can't deliver.
    smtp.connect(socket.gethostname(), smtp_port)
    #smtp.set_debuglevel(1)
    try:
        yield smtp
    finally:
        smtp.quit()

@yield_fixture
def sendmail(smtp):
    def f(body='test message', Sender=pwd.getpwuid(os.getuid()).pw_name + '@' + socket.gethostname(), headers={}, **kwargs):
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
    yield f

@fixture
def dummy_address():
    return None

@yield_fixture
def dummy_interface(dummy_address):
    ip = pyroute2.IPRoute()
    idx = ip.link_lookup(ifname='host0')[0]
    try:
        if dummy_address is not None:
            prefixlen = 128 if ':' in dummy_address else 32
            ip.addr('add', index=idx, address=dummy_address, prefixlen=prefixlen)
            # We can't bind to the address until duplicate address detection finishes
            for x in range(100):
                i = next((i for i in ip.get_addr() if i['index'] == idx and dict(i['attrs'])['IFA_ADDRESS'] == dummy_address), None)
                assert i is not None, 'the address we just added has disappeared'
                if i['flags'] & IFA_F_TENTATIVE == 0:
                    break
                time.sleep(0.1)
            else:
                assert 0, 'timed out waiting for address to lose tentative flag'
        yield
    finally:
        if dummy_address is not None:
            ip.addr('delete', index=idx, address=dummy_address, prefixlen=prefixlen)
