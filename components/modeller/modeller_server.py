#! /usr/bin/env python
import harp_pb2
import gflags
import modeller
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
gflags.DEFINE_integer('max_models_to_return', 5, 'Maximum number of models to return')
gflags.DEFINE_integer('models_per_alignment', 5, 'Number of models to generate for each alignment')

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
    logger.info('Processing job=%s, recipient=%s, alignments=%d' % (req.identifier, req.recipient, len(req.alignments)))

    # In order to prevent filename collisions, independent runs of modeller
    # are executed in separate directories
    curr_dir = os.getcwd()
    work_dir = tempfile.mkdtemp()
    os.chdir(work_dir)

    # Populate required fields in the response
    rep.recipient = req.recipient
    rep.identifier = req.identifier

    # Collection of (model, alignment, score)
    candidates = []

    for alignment in req.alignments:
        query_id = 'query'
        templ_id = str(alignment.templ_pdb + alignment.templ_chain)

        # Write template structure
        templ_file = templ_id + '.pdb'
        with open(templ_file, 'w') as file:
            file.write('%s\n' % alignment.templ_structure)

        # Write alignment
        alignment_file = templ_id + '.ali'
        with open(alignment_file, 'w') as file:
            params = { 'query_id'    : query_id,
                       'query_start' : alignment.query_start,
                       'query_stop'  : alignment.query_stop,
                       'query_align' : alignment.query_align }

            query_line = query_alignment.safe_substitute(params)

            params = { 'templ_id'    : templ_id,
                       'templ_pdb'   : templ_file,
                       'templ_chain' : alignment.templ_chain,
                       'templ_start' : alignment.templ_start,
                       'templ_stop'  : alignment.templ_stop,
                       'templ_align' : alignment.templ_align }

            templ_line = templ_alignment.safe_substitute(params)

            file.write('%s\n' % query_line)
            file.write('%s\n' % templ_line)

        # Run modeler
        modeller.log.verbose()

        env = modeller.environ()
        env.io.atom_files_directory = ['.']
        am = automodel(env,
                       alnfile = alignment_file,
                       knowns = templ_id,
                       sequence = query_id,
                       assess_methods = (DOPE, GA341))

        am.starting_model = 1
        am.ending_model   = FLAGS.models_per_alignment
        am.make()

        # Rank successful predictions by DOPE score
        models = [x for x in am.outputs if x['failure'] is None]
        models.sort(key = lambda x: x['DOPE score'])

        for model in models:
            with open(model['name']) as file:
                coords = ''
                for line in file:
                    coords += line
            
            entry = (coords, alignment, model['DOPE score'])
            candidates.append(entry)

    # After having generated N models for each alignment, select the best 5 by score
    candidates.sort(key = operator.itemgetter(-1))
    for (i, entry) in enumerate(candidates):
        coords, alignment, score = entry

        selection = rep.selected.add()
        selection.rank = i + 1

        # Message types cannot be assigned directory (e.g. x.field = field).
        # For additional details, read the "Singular Message Fields" section in:
        # https://developers.google.com/protocol-buffers/docs/reference/python-generated#fields
        selection.alignment.ParseFromString(alignment.SerializeToString())

        # Append alignment information to bottom of PDB file
        selection.model = coords
        selection.model += 'Source: %s\n' % alignment.method
        selection.model += 'Template: %s%s\n' % (alignment.templ_pdb, alignment.templ_chain)
        selection.model += 'Query alignment: %s\n' % alignment.query_align
        selection.model += 'Templ alignment: %s\n' % alignment.templ_align

        if (selection.rank == FLAGS.max_models_to_return):
            break

    os.chdir(curr_dir)
    shutil.rmtree(work_dir)
    logger.info('Completed job=%s, recipient=%s' % (req.identifier, req.recipient))


if __name__ == '__main__':
    try:
        sys.argv = FLAGS(sys.argv)
    except gflags.FlagsError, e:
        print '%s\\nUsage: %s ARGS\\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    # Setup logging
    logging.basicConfig(filename = 'modeller_server.log',
                        format = '%(asctime)-15s %(message)s',
                        level = logging.INFO)

    logger = logging.getLogger('modeller_server')

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
