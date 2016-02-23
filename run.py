#!/usr/bin/env python3
import logging
import yaml
import threading
import sys, time
import senders
import pymysql

from config import *

logging.basicConfig(format=logformat,
                    datefmt='%m/%d/%Y %H:%M:%S',
                    filename=filename,
                    level=logging.INFO)

def db_connect():
    try:
        db_conn = pymysql.connect(host = DB_Host,
                                  user = DB_User,
                                  passwd = DB_Password,
                                  db = DB_Name)
       # logging.debug("DB connected")
        return db_conn

    except pymysql.Error as e:
        logging.error(e)
        return None


def get_last_alert(notify_type='None'):
    db_conn = db_connect()
    if db_conn is None:
        sys.exit(1)

    cursor = db_conn.cursor()
    sql = """
        SELECT * FROM alerts
        WHERE status <> 0
        and alerttype = '%(notify_type)s'
        ORDER BY alertid
        LIMIT 1
        """%{"notify_type": notify_type}

    cursor.execute(sql)
    db_conn.commit()
    result = cursor.fetchone()
    cursor.close()
    db_conn.close()
    return result


def update_alert_status(alertid=0, status=9999, error='EMPTY', retries=999):
    db_conn = db_connect()
    cursor = db_conn.cursor()
    sql = """
    UPDATE alerts
        SET
           status = '%(status)s',
           error  = '%(error)s',
           retries = '%(retries)s'
        WHERE alertid = '%(alertid)s'
    """%{ "status": status,
          "error":  error,
          "alertid": alertid,
          "retries": retries}

    cursor.execute(sql)
    db_conn.commit()
    result = cursor.fetchone()
    cursor.close()
    db_conn.close()


def alerter(subscribers, notify_type):
    logging.info("Alerter " + notify_type + " started")

    while True:
        try:
            alert = get_last_alert(notify_type=notify_type)
            if alert is not None:
                alert_id = alert[0]
                event_id = alert[1]
                sendto = alert[4]
                subject = alert[5]
                message = alert[6]
                retries = alert[8]
                retries = int(retries) + 1

                result, error = senders.senders[notify_type]['sender'](sendto, subject, message, event_id)
                update_alert_status(alertid=alert_id,
                                    status=int(not result),
                                    error=error,
                                    retries=retries)

                print("[" + notify_type +  "] Message for: ", sendto,
                      "with subject'", subject,
                      "' sended:", result)

        except Exception as err:
            print(err)
        time.sleep(1)


if __name__ == '__main__':
    try:
        with open('subscribers.yaml', 'r') as file_pointer:
            subscribers = yaml.load(file_pointer)
            file_pointer.close()

    except Exception as err:
        print("ERROR: " + str(err))
        logging.error(err)
        sys.exit('1')

    try:
        listners_pool = {}
        sender_pool = {}
        for notify_type in senders.senders:
            if 'listner' in senders.senders[notify_type].keys():

                listners_pool[notify_type] = threading.Thread(target=senders.senders[notify_type]['listner'],
                                                          name="Listner " + str(notify_type))
                listners_pool[notify_type].start()
            if 'sender' in senders.senders[notify_type].keys():
                sender_pool[notify_type] = threading.Thread(target=alerter,
                                          kwargs={'subscribers': subscribers, "notify_type": notify_type},
                                          name="Alerter " + notify_type)
                sender_pool[notify_type].start()

    except Exception as err:
        logging.error(err)