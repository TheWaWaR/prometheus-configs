#!/usr/bin/env python
# coding: utf-8

import os
import json
import fcntl
import argparse
import smtplib
from email.mime.text import MIMEText

import yaml
from flask import Flask, request, current_app

app = Flask(__name__)
SMTP_TPL = "{key}: '{value}'"
SMTP_KEYS = [
    'smtp_smarthost',
    'smtp_from',
    'smtp_auth_username',
    'smtp_auth_password'
]


class Email(object):

    def __init__(self, smtp_server=None, smtp_port=None, smtp_ssl=True,
                 frm=None, to=None, passwd=None):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_ssl = smtp_ssl
        self.frm = frm
        self.to = to            # Default receiver
        self.passwd = passwd

    def init_app(self, app):
        cfg = app.config
        self.smtp_server = cfg['SMTP_SERVER']
        self.smtp_port = cfg['SMTP_PORT']
        self.smtp_ssl = cfg.get('SMTP_SSL', True)
        self.frm = cfg['MAIL_FROM']
        self.to = cfg['MAIL_TO_DEFAULT']
        self.passwd = cfg['MAIL_PASSWD']

    @property
    def session(self):
        Client = smtplib.SMTP_SSL if self.smtp_ssl else smtplib.SMTP
        s = Client(self.smtp_server, self.smtp_port)
        s.login(self.frm, self.passwd)
        return s

    def send(self, body, subject='[alertmanager]', type='plain', to=None):
        if to is None:
            to = self.to

        msg = MIMEText(body, type, 'utf-8')
        msg['subject'] = subject
        msg['from'] = self.frm
        msg['to'] = to

        retry = 3
        while retry > 0:
            try:
                self.session.sendmail(self.frm, to, msg.as_string())
                return True
            except smtplib.SMTPException as e:
                print e
                retry -= 1
        return False


@app.route('/prometheus/alert/webhook', methods=['POST'])
def alert_webhook():
    payload = json.loads(request.data)
    title = u'[告警]: {}'.format(payload['groupLabels']['alertname'])
    alerts = [
        '<li>[{}]: <strong>{}</strong><small>({})</small></li>'.format(
            item['status'],
            item['annotations']['summary'],
            item['annotations']['description']
        ) for item in payload['alerts']
    ]
    body = '\n'.join(['<ul>', '\n'.join(alerts), '</ul>'])
    current_app.mail.send(body, subject=title, type='html')
    return 'ok'


@app.route('/prometheus/alert/thresholds/', methods=['GET', 'POST'])
def alert_thresholds():
    with open(current_app.config['ARGS']['thresholds']) as f:
        print(u'Read from <{}>'.format(current_app.config['ARGS']['thresholds']))
        data = f.read()
    if request.method == 'GET':
        return data
    elif request.method == 'POST':
        thresholds = json.loads(data)
        new_thresholds = json.loads(request.data)
        for threshold in new_thresholds:
            alert_name = threshold['alert_name']
            if alert_name not in thresholds:
                return (u'Unknown alert_name={}'.format(alert_name), 403)
        for threshold in new_thresholds:
            thresholds[threshold['alert_name']] = threshold['value']

        lock_filename = current_app.config['ARGS']['lockfile']
        if not os.path.exists(lock_filename):
            open(lock_filename, 'a').close()
        with open(lock_filename) as lfd:
            fcntl.flock(lfd, fcntl.LOCK_EX)
            with open(current_app.config['ARGS']['thresholds'], 'w') as f:
                print(u'Write to <{}>'.format(current_app.config['ARGS']['thresholds']))
                json.dump(thresholds, f, indent=2)
            fcntl.flock(lfd, fcntl.LOCK_UN)
        return json.dumps(thresholds)


def get_alert_config():
    alertmanager_cfg_path = current_app.config['ARGS']['alertmanager']
    with open(alertmanager_cfg_path) as f:
        print(u'Read from {}'.format(alertmanager_cfg_path))
        cfg = yaml.load(f)
    rv_cfg = {'smtp': {}}
    for k in SMTP_KEYS:
        rv_cfg['smtp'][k] = cfg['global'].get(k)
    rv_cfg['email_to'] = cfg['receivers'][0]['email_configs'][0]['to']
    return rv_cfg


@app.route('/prometheus/alert/global', methods=['GET', 'POST'])
def alert_global():
    alertmanager_cfg_path = current_app.config['ARGS']['alertmanager']
    cfg = get_alert_config()
    if request.method == 'GET':
        return json.dumps({k: cfg['smtp'].get(k) for k in SMTP_KEYS})
    elif request.method == 'POST':
        new_cfg = json.loads(request.data)
        cfg_items = {_k: '' for _k in SMTP_KEYS}
        cfg_items['email_to'] = cfg['email_to']
        for key, value in new_cfg.iteritems():
            if value:
                cfg_items[key] = SMTP_TPL.format(key=key, value=value)
        with open('{}.tpl'.format(alertmanager_cfg_path)) as f:
            print(u'Read from <{}>'.format(alertmanager_cfg_path))
            content_tmpl = f.read()
            with open(alertmanager_cfg_path, 'w') as fw:
                print(u'Write to <{}>'.format(alertmanager_cfg_path))
                fw.write(content_tmpl % cfg_items)
        cfg_now = get_alert_config()
        return json.dumps({k: cfg_now['smtp'].get(k) for k in SMTP_KEYS})


@app.route('/prometheus/alert/recelvers/emails/', methods=['GET', 'POST'])
def alert_emails():
    cfg = get_alert_config()
    if request.method == 'GET':
        return json.dumps([cfg['email_to']])
    elif request.method == 'POST':
        alertmanager_cfg_path = current_app.config['ARGS']['alertmanager']
        new_emails = json.loads(request.data)
        cfg_items = {_k: '' for _k in SMTP_KEYS}
        cfg_items['email_to'] = new_emails[0]
        for key, value in cfg['smtp'].iteritems():
            if value:
                cfg_items[key] = SMTP_TPL.format(key=key, value=value)
        with open('{}.tpl'.format(alertmanager_cfg_path)) as f:
            print(u'Read from <{}>'.format(alertmanager_cfg_path))
            content_tmpl = f.read()
            with open(alertmanager_cfg_path, 'w') as fw:
                print(u'Write to <{}>'.format(alertmanager_cfg_path))
                fw.write(content_tmpl % cfg_items)
        return json.dumps([get_alert_config()['email_to']])


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-H', '--host', default='0.0.0.0')
    parser.add_argument('-p', '--port', type=int, default=3030)
    parser.add_argument('-c', '--config', required=True,
                        default='prometheus.yml')
    parser.add_argument('-a', '--alertmanager', required=True,
                        default='alertmanager.yml')
    parser.add_argument('-t', '--thresholds', required=True,
                        default='thresholds.json',
                        help='Alert thresholds file (.json)')
    parser.add_argument('-l', '--lockfile',
                        default='/tmp/prometheus-agent.lock')
    parser.add_argument('--smtp-server', required=True)
    parser.add_argument('--smtp-port', required=True)
    parser.add_argument('--mail-from', required=True)
    parser.add_argument('--mail-to', required=True)
    parser.add_argument('--mail-passwd', required=True)
    parser.add_argument('-D', '--debug', default=False, action='store_true')
    args = parser.parse_args()

    directory = os.path.dirname(args.config)
    for path in [args.config,
                 args.thresholds,
                 os.path.join(directory, 'alert.rules.tpl'),
                 os.path.join(directory, 'alertmanager.yml.tpl')]:
        if not os.path.exists(path):
            parser.error('File not exists: {0}'.format(path))
    return args


def main():
    args = parse_args()
    directory = os.path.dirname(args.config)
    with open(args.thresholds) as f:
        print(u'Read from <{}>'.format(args.thresholds))
        thresholds = json.load(f)
    with open(os.path.join(directory, 'alert.rules.tpl')) as fread:
        print(u'Read from <{}>'.format(os.path.join(directory, 'alert.rules.tpl')))
        rules_tmpl = fread.read()
        rules = rules_tmpl % thresholds
        rules_path = os.path.join(directory, 'alert.rules')
        with open(rules_path, 'w') as fwrite:
            print(u'Write to <{}>'.format(rules_path))
            fwrite.write(rules)

    app.config['SMTP_SERVER'] = args.smtp_server
    app.config['SMTP_PORT'] = args.smtp_port
    app.config['MAIL_FROM'] = args.mail_from
    app.config['MAIL_TO_DEFAULT'] = args.mail_to
    app.config['MAIL_PASSWD'] = args.mail_passwd
    app.config['ARGS'] = vars(args)
    mail = Email()
    mail.init_app(app)
    app.mail = mail

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
