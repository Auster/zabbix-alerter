#!/usr/bin/python3.4
import logging
import os
import sys
import urllib.request
from http import cookiejar
from urllib.parse import urlencode

import pymysql
import yaml

from config import *

level = logging.DEBUG

logging.basicConfig(format=logformat,
                    datefmt='%m/%d/%Y %H:%M:%S',
                    filename=filename,
                    level=level)

ZABBIX_USER = ZABBIX['user']
ZABBIX_SERVER = ZABBIX['server']
ZABBIX_PASSWORD = ZABBIX['password']

ZBX_severities_levels = {"Not classified": 0,
                         "Information": 1,
                         "Warning": 2,
                         "Average": 3,
                         "High": 4,
                         "Disaster": 5,
                         }


class FormatDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def db_connect():
    try:
        db_conn = pymysql.connect(host=DB_Host,
                                  user=DB_User,
                                  passwd=DB_Password,
                                  db=DB_Name)
        logging.debug("DB connected")
        return db_conn
    except pymysql.Error as e:
        logging.error(e)
        sys.exit(1)


def add_new_alert(alerttype='mail',
                  sendto='imakarov@axiomsl.com',
                  subject='SUBJECT',
                  message='MESSAGE',
                  status='0',
                  retries='0',
                  error='',
                  eventid='0'):
    db_conn = db_connect()
    cursor = db_conn.cursor()
    sql = """
    INSERT INTO alerts(eventid,
                      time,
                      alerttype,
                      sendto,
                      subject,
                      message,
                      status,
                      retries,
                      error)

    VALUES ('%(eventid)s',
            now(),
            '%(alerttype)s',
            '%(sendto)s',
            '%(subject)s',
            '%(message)s',
            '%(status)s',
            '%(retries)s',
            '%(error)s')

   """ % {"alerttype": alerttype,
          "sendto": sendto,
          "subject": subject,
          "message": message,
          "status": status,
          "retries": retries,
          "error": error,
          "eventid": eventid}

    cursor.execute(sql)
    db_conn.commit()
    logging.info("Alert added to DB(" + ")")
    return 1


def zbx_get_chart(ZABBIX_SERVER, ZABBIX_USER, ZABBIX_PASSWORD, item_id):
    jar = cookiejar.CookieJar()

    login_url = 'http://{zbx_srv}/index.php'.format(item_id=item_id, zbx_srv=ZABBIX_SERVER)
    img_url = 'http://{zbx_srv}/chart.php?period=7200&itemids={item_id}&width=600'.format(item_id=item_id,
                                                                                          zbx_srv=ZABBIX_SERVER)
    values = {'name': ZABBIX_USER,
              'password': ZABBIX_PASSWORD,
              'enter': 'Sign in'
              }

    data = urlencode(values).encode('utf8')

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    urllib.request.install_opener(opener)
    req = opener.open(login_url, data)
    img = opener.open(img_url)
    return img


if __name__ == '__main__':
    if len(sys.argv) != 4:
        logging.error('args != 4' + str(sys.argv))
        sys.exit(1)
    logging.debug('args: ' + str(sys.argv))

    string = sys.argv[3]  # .replace('\\\\', '\\')
    string = string.replace('\\r\\n', '\r')
    values = yaml.load(string)

    try:
        img = zbx_get_chart(ZABBIX_SERVER, ZABBIX_USER, ZABBIX_PASSWORD, item_id=values['ITEM_ID1'])
        file = open(CACHE_DIR + "/{EVENT_ID}.png".format(EVENT_ID=values['EVENT_ID']), "wb")
        file.write(img.read())
        file.close()
    except Exception as err:
        logging.error(err)

    try:
        with open(os.path.dirname(__file__) + '/subscribers.yaml', 'r') as file_pointer:
            subscribers = yaml.load(file_pointer)
            file_pointer.close()

        with open(os.path.dirname(__file__) + '/messages.yaml', 'r') as file_pointer:
            messages_raw = yaml.load(file_pointer)
            file_pointer.close()

            mapping = FormatDict(values)

            messages = {}

            for notify_type in messages_raw:
                subject = messages_raw[notify_type][values['TRIGGER_STATUS']]['subject'].format_map(mapping)
                body = messages_raw[notify_type][values['TRIGGER_STATUS']]['body'].format_map(mapping)

                if notify_type not in messages:
                    messages[notify_type] = {}

                if values['TRIGGER_STATUS'] not in messages[notify_type]:
                    messages[notify_type][values['TRIGGER_STATUS']] = {}

                messages[notify_type][values['TRIGGER_STATUS']]['subject'] = subject
                messages[notify_type][values['TRIGGER_STATUS']]['body'] = body

    except Exception as err:
        print("ERROR: " + str(err))
        logging.error(err)
        sys.exit(1)

    for subscriber in subscribers:
        for notify_type in subscribers[subscriber]:
            criticality = subscribers[subscriber][notify_type]['criticality']
            notify_type_criticality = ZBX_severities_levels[criticality]
            trigger_criticality = ZBX_severities_levels[values['TRIGGER_SEVERITY']]

            if trigger_criticality >= notify_type_criticality:
                send_to = subscribers[subscriber][notify_type]['dest']
                subject = messages[notify_type][values['TRIGGER_STATUS']]['subject']
                body = messages[notify_type][values['TRIGGER_STATUS']]['body']
                eventid = values['EVENT_ID']

                print(send_to)
                print(body)
                print(subject)

                try:
                    add_new_alert(alerttype=notify_type,
                                  sendto=send_to,
                                  subject=subject,
                                  message=body,
                                  status='1',
                                  retries='0',
                                  error='',
                                  eventid=eventid)
                    logging.info("Added: " + subject + " " + str(eventid))
                except Exception as err:
                    logging.error(err)
                    logging.error(values)
