import logging
import os
import smtplib
import uuid
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import *


class FormatDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def sender(to, subject, body, action_id):
    msg = MIMEMultipart('related')
    msg_alternative = MIMEMultipart('alternative')
    msg.attach(msg_alternative)

    sendfrom = MAILSendFrom
    msg['Subject'] = subject
    msg['From'] = sendfrom
    msg['To'] = to

    chart_filename = str(action_id) + '.png'
    img_path = CACHE_DIR + '/' + chart_filename
    img = dict(title=u'Chart', path=img_path, cid=str(uuid.uuid4()))

    try:
        msg_text = MIMEText(u'[image: {title}]'.format(title=img['title']), 'plain', 'utf-8')
        msg_alternative.attach(msg_text)
        mapping = FormatDict({'cid': img['cid']})
        msg_html = MIMEText(body.format_map(mapping), 'html', 'utf-8')
        msg_alternative.attach(msg_html)
        with open(img['path'], 'rb') as file:
            msg_image = MIMEImage(file.read(), name=os.path.basename(img['path']))
            msg.attach(msg_image)
        msg_image.add_header('Content-ID', '<{}>'.format(img['cid']))

        s = smtplib.SMTP(MAILServer, 587)
        s.ehlo()
        s.starttls()
        s.ehlo()
        s.login(MAILUser, MAILPassword)
        s.sendmail(sendfrom, to, msg.as_string())
        s.quit()

        logging.info("Mail sended to: " + str(to))
        return True, "ok"

    except Exception as err:
        logging.error("Mail error: " + str(err))
        print(err)
        return False, str(err)
