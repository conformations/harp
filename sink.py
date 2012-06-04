#! /usr/bin/env python
from proto_util import *
import gmail
import harp_pb2

import gflags
import zmq

from email.encoders import encode_base64
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
import os.path
import sys

# Gmail account information
GMAIL = '/home/modeller/conf/gmail.conf'

FLAGS = gflags.FLAGS
gflags.DEFINE_string('incoming', 'tcp://localhost:8001', 'Incoming socket')

def process(username, password, rep):
    msg = MIMEMultipart()
    msg['Subject'] = 'HARP results -- %s' % rep.identifier
    msg['From'] = username
    msg['To'] = rep.recipient

    # Construct the reply email and a series of attachments
    for selected in rep.selected:
        filename = 'model%d.pdb' % selected.rank

        part = MIMEBase('application', "octet-stream")
        part.set_payload(selected.model)
        encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % filename)

        msg.attach(part)

    gmail.send(username, password, msg)


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
        sys.stderr.write('Failed to connect incoming socket: %s\n' % FLAGS.incoming)
        sys.exit(1)

    # Load account information from file
    assert os.path.exists(GMAIL)
    username, password = gmail.account_info(GMAIL)

    while True:
        sender_uid = fe.recv()
        rep = harp_pb2.HarpResponse()

        proto_recv(fe, rep)
        process(username, password, rep)
