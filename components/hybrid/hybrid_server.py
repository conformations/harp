#! /usr/bin/env python
import harp_pb2
import gflags
from proto_util import *
import zmq

import logging
import operator
import os
import shutil
import string
import sys
import tempfile

FLAGS = gflags.FLAGS
gflags.DEFINE_string('incoming', 'tcp://localhost:8001', 'Incoming socket')
gflags.DEFINE_string('outgoing', 'tcp://localhost:8002', 'Outgoing socket')

gflags.DEFINE_string('rosetta_dir', '/home/cmiles/src/rosetta', 'Absolute path to rosetta directory')
gflags.DEFINE_string('cm_dir', '/home/cmiles/src/cm_scripts', 'Absolute path to cm_scripts directory')

gflags.DEFINE_integer('max_models_to_return', 5, 'Maximum number of models to return')
gflags.DEFINE_integer('models_per_alignment', 5, 'Number of models to generate for each alignment')


def process(req, rep):
    '''Processes a single request to the server, storing the result in `rep`'''
    # In order to prevent filename collisions, independent runs of Rosetta
    # are executed in separate directories
    curr_dir = os.getcwd()
    work_dir = tempfile.mkdtemp()
    os.chdir(work_dir)

    # Populate required fields in the response
    rep.recipient = req.recipient
    rep.identifier = req.identifier

    # setup_cm
    # setup_hybridize
    # run locally
    # select_best_models

    # Populate proto

    os.chdir(curr_dir)
    shutil.rmtree(work_dir)


if __name__ == '__main__':
    try:
        sys.argv = FLAGS(sys.argv)
    except gflags.FlagsError, e:
        print '%s\\nUsage: %s ARGS\\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    # Setup logging
    logging.basicConfig(filename = 'hybrid_server.log',
                        format = '%(asctime)-15s %(message)s',
                        level = logging.INFO)

    logger = logging.getLogger('hybrid_server')

    # Setup ZeroMQ
    context = zmq.Context()
    fe = context.socket(zmq.PULL)
    be = context.socket(zmq.PUSH)

    try:
        fe.connect(FLAGS.incoming)
    except:
        sys.stderr.write('Failed to connect incoming socket: %s\n' % FLAGS.incoming)
        sys.exit(1)

    try:
        be.connect(FLAGS.outgoing)
    except:
        sys.stderr.write('Failed to connect outgoing socket: %s\n' % FLAGS.outgoing)
        sys.exit(1)

    while True:
        sender_uid = fe.recv()
        req = harp_pb2.ModelingRequest()
        rep = harp_pb2.HarpResponse()

        try:
            proto_recv(fe, req)

            try:
                process(req, rep)
                proto_send(be, rep)
            except Exception as e:
                logger.error('Error occurred while processing request')
                logger.error(e)

        except Exception as e:
            logger.error('Failed to parse incoming message; expected HarpResponse')
            logger.error(e)
