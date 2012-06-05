#! /usr/bin/env python
from proto_util import *
import gmail
import harp_pb2

import gflags
import zmq

import email.encoders
import email.mime.base
import email.mime.multipart
import logging
import os.path
import sys

# Logging configuration
logging.basicConfig(format = '%(asctime)-15s %(message)s')
logger = logging.getLogger('sink')

# Command line flags
FLAGS = gflags.FLAGS
gflags.DEFINE_string('conf', '/home/modeller/conf/gmail.conf', 'JSON-format configuration file')
gflags.DEFINE_string('incoming', 'tcp://localhost:8005', 'Incoming socket')


def process(username, password, rep):
    '''Constructs and sends the reply email for a single job'''
    logger.info('Processing response for job=%s, recipient=%s, models=%d' % (rep.identifier, rep.recipient, len(rep.selected)))
    
    msg = email.mime.multipart.MIMEMultipart()
    msg['Subject'] = 'HARP results -- %s' % rep.identifier
    msg['From'] = username
    msg['To'] = rep.recipient

    # Construct the reply email and attach selected models
    for selected in rep.selected:
        part = email.mime.base.MIMEBase('application', "octet-stream")
        part.set_payload(selected.model)
        email.encoders.encode_base64(part)

        filename = 'model%d.pdb' % selected.rank
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % filename)
        msg.attach(part)

    # Attempt to send the reply email
    status = True
    try:
        gmail.send(username, password, msg)
    except:
        status = False
    finally:
        logger.info('Sent response email for job=%s to recipient=%s, status=%s' % (rep.identifier, rep.recipient, status))


if __name__ == '__main__':
    try:
        sys.argv = FLAGS(sys.argv)
    except gflags.FlagsError, e:
        print '%s\\nUsage: %s ARGS\\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    context = zmq.Context()
    fe = context.socket(zmq.PULL)

    try:
        fe.connect(FLAGS.incoming)
    except:
        logger.error('Failed to connect incoming socket: %s' % FLAGS.incoming)
        sys.exit(1)

    # Load account information from file
    assert os.path.exists(FLAGS.conf)
    username, password = gmail.account_info(FLAGS.conf)

    while True:
        sender_uid = fe.recv()
        rep = harp_pb2.HarpResponse()
        proto_recv(fe, rep)
        process(username, password, rep)
