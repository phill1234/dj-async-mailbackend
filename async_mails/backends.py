import base64
from collections import OrderedDict
from email.mime.base import MIMEBase
import os
from celery import Celery
from django.core.mail.backends.base import BaseEmailBackend

celery = Celery(broker=os.getenv('CELERY_BROKER_URL'))


class AsyncEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        for message in email_messages:
            message_dict = {}

            # This reverses the order of the alternative tuples and converts it into a dict
            html = OrderedDict(map(lambda t: (t[1], t[0]), message.alternatives)).get("text/html")

            if html is None:
                html = message.body

            message_dict.update({
                "mail_from": message.from_email,
                "mail_to": message.to,
                "cc": message.cc,
                "bcc": message.bcc,
                "subject": message.subject,
                "html": html,
                "text": message.body,
                "attachments": [],
            })

            for attachment in message.attachments:
                if isinstance(attachment, MIMEBase):
                    filename = attachment.get_filename('')
                    binary_contents = attachment.get_payload(decode=True)
                    mimetype = attachment.get_content_type()
                else:
                    filename, binary_contents, mimetype = attachment

                content = base64.b64encode(binary_contents).decode('ascii')
                message_dict['attachments'].append((filename, content, mimetype))

            # Send task to Celery Worker
            celery.send_task(
                'tasks.send_mail',
                kwargs=message_dict
            )
