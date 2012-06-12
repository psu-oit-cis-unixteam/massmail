#!/usr/bin/env python

import datetime
import email
import hashlib
import ldap
import logging
import random
import smtplib
import sys
import os

from config import ldap as settings
logger = logging.getLogger(__name__)


def test_email_list(query):
    email = []
    for i in range(2000):
        email.append( query % ( hashlib.sha1(str(random.random())).hexdigest(), ))
    return email
   
def ldap_email_list(query):

    l = ldap.open( settings['server'] )
    l.simple_bind_s(settings['who'], settings['cred'])
    r = l.search(settings['base'], ldap.SCOPE_SUBTREE,
                 query, ['mail'])
    emails = []
    while True:
        (code, result) = l.result(r,0)
        if code != 100:
            break
        try:
            [(_,b)] = result
            emails.append( b['mail'][0] )

        except:
            print result

    logging.info('added %d emails' % (len(emails),))
    return emails

def resolve_target(target):

    target = 't'

    email = []

    if 't' in target:
        logging.info('adding test user')
        email += test_email_list('nobody+%s@pdx.edu')
    if 's' in target:
        logging.info('adding students')
        #email += ldap_email_list('eduPersonAffiliation=EMPLOYEE*')
    if 'f' in target:
        logging.info('adding employees')
        #email += ldap_email_list('eduPersonAffiliation=STUDENT*')

    logging.info('total: %d emails' % (len(email),))
    email = list(set(email))
    logging.info('deduping. now %d' % (len(email),))

    return email

def send_mail(config):
    emails = resolve_target(config['TARGET'])

    msg = email.MIMEMultipart.MIMEMultipart()
    msg['Subject'] = config['SUBJECT']
    msg['From'] = "%s <%s>" %( config['FROM_NAME'], config['FROM_ADDRESS'])
    msg['To'] = ''

    msg.add_header('Precedence','bulk')
    msg.attach(email.MIMEText.MIMEText( config['BODY'],'plain', _charset='en_US.UTF-8' ))

    server = smtplib.SMTP(settings['mailhost'])
    #server.set_debuglevel(1)

    click = datetime.datetime.now()

    for i, target in enumerate(emails):

        if ( datetime.datetime.now() - click).seconds > 60:
            server.quit()
            server = smtplib.SMTP(settings['mailhost'])
        
        msg.replace_header('To', target)
        try:
            server.sendmail(config['FROM_ADDRESS'], target, msg.as_string())
            logging.info('mail send: %s ok %d/%d' %( target, (i+1), len(emails)) )
        except Exception, e:
            logging.error('mail send: %s failed. %s' %( target, e))
            
    server.quit()


def parse_mail(mail_filename):
    
    mailfile = file(mail_filename,'rb')

    config = {}
    while True:
        i = mailfile.readline()
        a = i.split(':')
        key = a.pop(0)
        config[ key ] = ':'.join(a).strip()
        if key =='BODY':
            break
        
    config['BODY'] = ''.join(mailfile.xreadlines()).strip()
    # validate data better here.
    return config

def main():

    filename = None

    if len(sys.argv) == 3:
        if os.path.exists(sys.argv[2]) and \
           os.path.isfile(sys.argv[2]) and \
           os.access(sys.argv[2], os.R_OK):
            filename = sys.argv[2]

    if filename == None:
        print "%s:usage -i <filename>" %( sys.argv[0],)
        sys.exit(1)

    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M:%S',
                        filename='%s.log' %(filename,),
                        filemode='w')

    c = parse_mail( filename )

    send_mail(c)
    
if __name__ == "__main__":
    main()





