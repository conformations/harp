#! /usr/bin/env python
import harp_pb2
import gflags
import modeller
from proto_util import *
import zmq

import operator
import string
import sys

FLAGS = gflags.FLAGS
gflags.DEFINE_string('incoming', 'tcp://localhost:8001', 'Incoming socket')
gflags.DEFINE_string('outgoing', 'tcp://localhost:8002', 'Outgoing socket')

query_alignment = string.Template('''
>P1;$query_id
sequence:$query_id:$query_start::$query_stop::::0.00:0.00
$query_align*
''')

templ_alignment = string.Template('''
>P1;$templ_id
structureX:$templ_pdb:$templ_start:$templ_chain:$templ_stop:$templ_chain:undefined:undefined:-1.00:-1.00
$templ_align*
''')

def process(req, rep):
    '''Processes a single request to the server, storing the result in `rep`'''
    from modeller.automodel.assess import DOPE, GA341
    from modeller.automodel import automodel

    # Populate required fields in the response
    rep.recipient = req.recipient
    rep.identifier = req.identifier

    # Collection of (model, score)
    candidates = []

    for a in req.alignments:
        assert a.query_start == 1
        assert a.query_stop == len(req.sequence)

        query_id = 'query'
        templ_id = str(a.templ_pdb + a.templ_chain)

        # Write template structure
        templ_file = templ_id + '.pdb'
        with open(templ_file, 'w') as file:
            file.write('%s\n' % a.templ_structure)

        # Write alignment
        alignment_file = templ_id + '.ali'
        with open(alignment_file, 'w') as file:
            params = { 'query_id'    : query_id,
                       'query_start' : a.query_start,
                       'query_stop'  : a.query_stop,
                       'query_align' : a.query_align }

            query_line = query_alignment.safe_substitute(params)

            params = { 'templ_id'    : templ_id,
                       'templ_pdb'   : templ_file,
                       'templ_chain' : a.templ_chain,
                       'templ_start' : a.templ_start,
                       'templ_stop'  : a.templ_stop,
                       'templ_align' : a.templ_align }

            templ_line = templ_alignment.safe_substitute(params)

            file.write('%s\n' % query_line)
            file.write('%s\n' % templ_line)

        # Run modeler
        modeller.log.verbose()

        env = modeller.environ()
        env.io.atom_files_directory = ['.']
        a = automodel(env,
                      alnfile = alignment_file,
                      knowns = templ_id,
                      sequence = query_id,
                      assess_methods = (DOPE, GA341))

        a.starting_model = 1  # index of first generated model
        a.ending_model   = 5  # index of final generated model
        a.make()

        # Rank successful predictions by DOPE score
        models = [x for x in a.outputs if x['failure'] is None]
        models.sort(key = lambda a: a['DOPE score'])

        for m in models:
            with open(m['name']) as file:
                coords = ''
                for line in file:
                    coords += line
            
            entry = (coords, m['DOPE score'])
            candidates.append(entry)

    # After having generated N models for each alignment, select the best 5 by score
    candidates.sort(key = operator.itemgetter(1))
    for (i, candidate) in enumerate(candidates):
        selection = rep.selected.add()
        selection.model = candidate
        selection.rank = i + 1

        if (selection.rank == 5):
            break


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
        
