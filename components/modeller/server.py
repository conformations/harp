#! /usr/bin/env python
import harp_pb2
import gflags
from proto_util import *

import modeller
import zmq

import os
import os.path
import shutil
import string
import subprocess
import sys
import tempfile

FLAGS = gflags.FLAGS
gflags.DEFINE_string('incoming', 'tcp://localhost:8001', 'Incoming socket')
gflags.DEFINE_string('outgoing', 'tcp://localhost:8002', 'Outgoing socket')

def process(req, rep):
    '''Processes a single request to the server, storing the result in `rep`'''
    from modeller.automodel.assess import DOPE, GA341
    from modeller.automodel import automodel

    # Populate required fields in the response
    rep.recipient = req.recipient
    rep.identifier = req.identifier

    # Return immediately when no alignments were found
    if not req.alignments:
        return

    # In order to prevent filename collisions, each execution of modeller is
    # performed in a separate temporary directory
    base_dir = os.getcwd()
    work_dir = tempfile.mkdtemp()
    os.chdir(work_dir)

    query = 'q'
    templates = [a.templ_pdb + a.templ_chain for a in req.alignments]

    alignment = 'alignment'
    with open(alignment, 'w') as file:
        pass

    # Validate inputs
    assert os.path.exists(alignment)

    env = modeller.environ()
    a = automodel(env, alnfile = alignment, knowns = templates, sequence = query, assess_methods = (DOPE, GA341))

    a.starting_model = 1  # index of first generated model
    a.ending_model   = 5  # index of final generated model
    a.make()

    # Rank successful predictions by DOPE score
    models = [x for x in a.outputs if x['failure'] is None]
    models.sort(key = lambda a: a['DOPE score'])

    for (i, model) in enumerate(models):
        selection = rep.selected.add()
        selection.rank = i + 1

        with open(model['name']) as file:
            for line in file:
                selection.model += line

    os.chdir(base_dir)
    shutil.rmtree(work_dir)


if __name__ == '__main__':
    try:
        sys.argv = FLAGS(sys.argv)
    except gflags.FlagsError, e:
        print '%s\\nUsage: %s ARGS\\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

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

        proto_recv(fe, req)
        process(req, rep)
        proto_send(be, rep)
        
