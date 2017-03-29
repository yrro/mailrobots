import smtplib

from pytest import *

def test_clamav(sendmail, print_logs, print_journal):
    try:
        with raises(smtplib.SMTPDataError) as excinfo:
            sendmail(To='account@test.example', Subject='clamav test', body='Virus message, should be blocked\r\n' r'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' '\r\n')
        assert (550, b'Malware detected in message (Eicar-Test-Signature)') == excinfo.value.args
    finally:
        print_logs()
        print_journal()
