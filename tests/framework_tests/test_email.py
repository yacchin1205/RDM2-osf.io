# -*- coding: utf-8 -*-
import unittest
import smtplib

from unittest import mock
from sendgrid.helpers.mail import Mail

from framework.email.tasks import send_email, _send_with_sendgrid
from website import settings
from tests.base import fake
from osf_tests.factories import fake_email

# Check if local mail server is running
SERVER_RUNNING = True
try:
    s = smtplib.SMTP(settings.MAIL_SERVER)
    s.quit()
except Exception as err:
    SERVER_RUNNING = False


class TestEmail(unittest.TestCase):

    @unittest.skipIf(not SERVER_RUNNING,
                     "Mailserver isn't running. Run \"invoke mailserver\".")
    @unittest.skipIf(not settings.USE_EMAIL,
                     'settings.USE_EMAIL is False')
    def test_sending_email(self):
        assert (send_email('foo@bar.com', 'baz@quux.com', subject='no subject',
                                 message='<h1>Greetings!</h1>', ttls=False, login=False))

    def test_send_with_sendgrid_success(self):
        mock_client = mock.MagicMock()
        mock_client.send.return_value.status_code = 200
        from_addr, to_addr = fake_email(), fake_email()
        cc_addr = fake_email()
        replyto = fake_email()
        category1, category2 = fake.word(), fake.word()
        subject = fake.bs()
        message = fake.text()
        ret = _send_with_sendgrid(
            from_addr=from_addr,
            to_addr=to_addr,
            subject=subject,
            message=message,
            mimetype='html',
            client=mock_client,
            categories=(category1, category2),
            cc_addr=cc_addr,
            replyto=replyto,
        )
        assert (ret)

        assert (mock_client.send.call_count) == (1)
        # First call's argument should be a Mail object with
        # the correct configuration
        first_call_arg = mock_client.send.call_args[0][0]
        assert isinstance(first_call_arg, Mail)
        mail_data = first_call_arg.get()
        assert mail_data['from']['email'] == from_addr
        assert mail_data['personalizations'][0]['to'] == [{'email': to_addr}]
        assert mail_data['personalizations'][0]['cc'] == [{'email': cc_addr}]
        assert mail_data['reply_to']['email'] == replyto
        assert mail_data['subject'] == subject
        assert mail_data['content'] == [{'type': 'text/html', 'value': message}]
        assert set(mail_data['categories']) == {category1, category2}

    def test_send_with_sendgrid_failure_returns_false(self):
        mock_client = mock.MagicMock()
        mock_client.send.return_value.status_code = 400
        from_addr, to_addr = fake_email(), fake_email()
        subject = fake.bs()
        message = fake.text()
        ret = _send_with_sendgrid(
            from_addr=from_addr,
            to_addr=to_addr,
            subject=subject,
            message=message,
            mimetype='html',
            client=mock_client
        )
        assert not (ret)


if __name__ == '__main__':
    unittest.main()
