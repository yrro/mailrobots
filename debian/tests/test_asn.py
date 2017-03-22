from pytest import *

@mark.parametrize('dummy_address', ['216.58.201.46', '2a00:1450:4009:80f::200e'])
@mark.usesfixtures('dummy_interface')
def test_asn(sendmail, imap, print_logs, print_journal):
    try:
        sendmail(To='account@test.example', Subject='asn test')
        imap.select()
        status, uids = imap.uid('search', 'subject "asn test"')
        assert status == 'OK'
        status, x = imap.uid('fetch', uids[0].split()[0], '(body[header.fields (x-asn)])')
        assert status == 'OK'
        assert b'AS15169 Google Inc.' in x[0][1]
    finally:
        print_logs()
        print_journal()
