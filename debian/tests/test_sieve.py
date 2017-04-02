import os
import shutil
import subprocess

from pytest import *

def test_spam_delivered_to_spam_mailbox(lsendmail, imap, print_journal):
    try:
        lsendmail(To='account@test.example', Subject='spam sieve test', headers={'X-Spam-Status': 'score=8.0 required=5.0'})
        status, dat = imap.select('Spam')
        assert 'OK' == status
        status, uids = imap.uid('search', 'subject "spam sieve test"')
        assert 'OK' == status
        status, resp = imap.uid('fetch', uids[0].split()[0], '(flags)')
        assert 'OK' == status
        assert b'1 (UID 1 FLAGS (\\Recent Junk $Junk))' == resp[0]
    finally:
        print_journal()

def test_user_sieve_script(lsendmail, imap, managesieve, print_journal):
    try:
        managesieve.putscript('test',
            'require ["fileinto", "mailbox"];'
            'if address :is "from" "blah@blah.com" {'
                'fileinto :create "blah";'
                'stop;'
            '}'
        )
        managesieve.setactive('test')
        lsendmail(To='account@test.example', Subject='sieve test', From='blah@blah.com')
        status, dat = imap.select('blah')
        assert 'OK' == status
        assert ('OK', [b'1']) == imap.uid('search', 'subject "sieve test"')
    finally:
        print_journal()

def test_user_sieve_script_doesnt_prevent_global_spam_sieve_script(lsendmail, imap, managesieve, print_journal):
    try:
        managesieve.putscript('test',
            'require ["fileinto", "mailbox"];'
            'if address :is "from" "blah@blah.com" {'
                'fileinto :create "blah";'
                'stop;'
            '}'
        )
        managesieve.setactive('test')
        lsendmail(To='account@test.example', Subject='spam sieve test', headers={'X-Spam-Status': 'score=8.0 required=5.0'})
        status, dat = imap.select('Spam')
        assert 'OK' == status
        status, uids = imap.uid('search', 'subject "spam sieve test"')
        assert 'OK' == status
        status, resp = imap.uid('fetch', uids[0].split()[0], '(flags)')
        assert 'OK' == status
        assert b'1 (UID 1 FLAGS (\\Recent Junk $Junk))' == resp[0]
    finally:
        print_journal()

@yield_fixture
def mock_spamc_learn():
    try:
        subprocess.check_call(['dpkg-divert', '--local', '--rename', '--add', '/usr/lib/mailrobots/sieve-pipe/spamc-learn'])
        with open('/usr/lib/mailrobots/sieve-pipe/spamc-learn', 'w') as f:
            f.write(
                  '#!/bin/bash\n'
                  'echo USER="$USER" >>/spamc-learn/output\n'
                  'echo @="$@" >>/spamc-learn/output\n'
            )
        os.chmod('/usr/lib/mailrobots/sieve-pipe/spamc-learn', 0o755)
        os.mkdir('/spamc-learn')
        shutil.chown('/spamc-learn', 'mailstorage', 'mailstorage')
        yield '/spamc-learn/output'
    finally:
        if os.path.exists('/spamc-learn'):
            shutil.rmtree('/spamc-learn')
        os.remove('/usr/lib/mailrobots/sieve-pipe/spamc-learn')
        subprocess.check_call(['dpkg-divert', '--rename', '--remove', '/usr/lib/mailrobots/sieve-pipe/spamc-learn'])

@mark.parametrize('verb', ['COPY', 'MOVE'])
def test_tell_spam(lsendmail, imap, verb, print_journal, mock_spamc_learn):
    try:
        lsendmail(To='account@test.example', Subject='spam tell test', headers={'X-Spam-Status': 'score=1.0 required=5.0'})
        status, dat = imap.select('INBOX')
        assert 'OK' == status
        status, uids = imap.uid('search', 'subject "spam tell test"')
        assert 'OK' == status
        status, resp = imap.uid(verb, uids[0].split()[0], 'Spam')
        assert 'OK' == status
        status, dat = imap.select('Spam')
        assert 'OK' == status
        assert ('OK', [b'1']) == imap.uid('search', 'subject "spam tell test"')
        with open(mock_spamc_learn) as f:
            assert ['USER=account@test.example\n', '@=spam\n'] == f.readlines()
    finally:
        print_journal()

@mark.parametrize('verb', ['COPY', 'MOVE'])
def test_tell_ham(lsendmail, imap, verb, print_journal, mock_spamc_learn):
    try:
        lsendmail(To='account@test.example', Subject='ham tell test', headers={'X-Spam-Status': 'score=8.0 required=5.0'})
        status, dat = imap.select('Spam')
        assert 'OK' == status
        status, uids = imap.uid('search', 'subject "ham tell test"')
        assert 'OK' == status
        status, resp = imap.uid(verb, uids[0].split()[0], 'INBOX')
        status, dat = imap.select('INBOX')
        assert 'OK' == status
        assert ('OK', [b'1']) == imap.uid('search', 'subject "ham tell test"')
        with open(mock_spamc_learn) as f:
            assert ['USER=account@test.example\n', '@=ham\n'] == f.readlines()
    finally:
        print_journal()

@mark.parametrize('verb', ['COPY', 'MOVE'])
def test_trash_spam_no_tell(lsendmail, imap, verb, print_journal, mock_spamc_learn):
    try:
        lsendmail(To='account@test.example', Subject='spam trash test', headers={'X-Spam-Status': 'score=8.0 required=5.0'})
        status, dat = imap.create('Trash')
        assert 'OK' == status
        status, dat = imap.select('Spam')
        assert 'OK' == status
        status, uids = imap.uid('search', 'subject "spam trash test"')
        assert 'OK' == status
        status, resp = imap.uid(verb, uids[0].split()[0], 'Trash')
        assert 'OK' == status
        status, dat = imap.select('Trash')
        assert 'OK' == status
        assert ('OK', [b'1']) == imap.uid('search', 'subject "spam trash test"')
        assert not os.path.exists(mock_spamc_learn)
    finally:
        print_journal()

def test_sieve_mtime():
    s1 = os.stat('/var/lib/mailrobots/sieve/after/100_spam.sieve')
    s2 = os.stat('/var/lib/mailrobots/sieve/after/100_spam.svbin')
    assert s1.st_mtime < s2.st_mtime
