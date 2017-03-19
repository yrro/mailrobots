import functools
import mailbox
import os
import shutil
import subprocess
import sys
import time

import pytest

aliases_text = '''
alias account
^pattern account
'''

passwd_in_text = '''
[user:account]
password = $6$CE0MQhhj0wGYjq2$jMtQd5En/oYHT7Uwbeb/IGuf1K9iWKIAUhHAIXVcwXJifC7gxT4al0BU0UE3aKtUiFXlYkC7cNW2ypohRmfz0.
quota = 100KB
'''

def sendmail(body, **kwargs):
    p = subprocess.Popen(['/usr/sbin/sendmail', '-ti'], stdin=subprocess.PIPE)
    msg = []
    for k, v in kwargs.items():
        msg.append(k.encode('ascii') + b': ' + v.encode('ascii'))
    msg.append(b'')
    msg.append(body.encode('ascii'))
    p.communicate(b'\n'.join(msg))
    if p.wait() != 0:
        raise Exception('sendmail failed')

def print_file(path):
    print('... ' + path)
    try:
        print(open(path).read())
    except OSError as e:
        print(e, file=sys.stderr)

@pytest.yield_fixture
@pytest.fixture#(scope='session')
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

    # The mailbox isn't actaully created until mail is sent to it, so hand a
    # mailbox factory to the test
    yield functools.partial(mailbox.Maildir, '/srv/mail/domains/test.example/users/account/Maildir', create=False)

    shutil.rmtree('/srv/mail/domains/test.example')
    os.remove('/srv/mail/passwd')

    if os.path.exists('/var/mail/mail'):
        os.remove('/var/mail/mail')

@pytest.mark.parametrize('address', [
    'alias',
    'pattern12345',
    'account',
    #'account-foo', # XXX wtf
    'account+foo',
])
def test_delivery(address, user_mailbox):
    sendmail('blah', To=address+'@test.example', Subject=address+' test')
    time.sleep(0.25)
    print_file('/var/mail/mail')
    assert any(lambda msg: msg['Subject'] == address+' test' for msg in user_mailbox())
