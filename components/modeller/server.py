#! /usr/bin/env python
import harp_pb2
from proto_util import *

import modeller
import zmq

import argparse
import os
import os.path
import shutil
import string
import subprocess
import sys
import tempfile

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
    parser = argparse.ArgumentParser()
    parser.add_argument('--in',  default = 'tcp://localhost:8001', help = 'Incoming socket')
    parser.add_argument('--out', default = 'tcp://localhost:8002', help = 'Outgoing socket')
    options = vars(parser.parse_args())

    context = zmq.Context()
    fe = context.socket(zmq.PULL)
    be = context.socket(zmq.PUSH)

    try:
        fe.connect(options['in'])
    except:
        sys.stderr.write('Failed to connect incoming socket: %s\n' % options['in'])
        sys.exit(1)

    try:
        be.connect(options['out'])
    except:
        sys.stderr.write('Failed to connect outgoing socket: %s\n' % options['out'])
        sys.exit(1)

    while True:
        sender_uid = fe.recv()
        req = harp_pb2.ModelingRequest()
        rep = harp_pb2.HarpResponse()

        proto_recv(fe, req)
        process(req, rep)
        proto_send(be, rep)
        
