#! /usr/bin/env python
import harp_pb2
import gflags
import modeller
from proto_util import *
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

    # Return immediately when no alignments were found
    if not req.alignments:
        return

    # In order to prevent file collisions, independent runs of modeller
    # are executed in separate, sandboxed directories
    curr_dir = os.getcwd()
    work_dir = tempfile.mkdtemp()
    os.chdir(work_dir)

    query = 'query'

    # Ensure that input alignments are full length. Simultaneously, generate
    # unique identifiers for each alignment in the unlikely event that they
    # share the same template pdb's, chains, etc.
    templates = []
    for a in req.alignments:
        assert a.query_start == 1
        assert a.query_stop == len(req.sequence)
        templ_id = [str(a.templ_pdb), str(a.templ_chain)]
        templates.append(templ_id)

    # Copy compressed template structures from local mirror of the wwpdb
    # into the working directory. Build up a list of template identifiers
    # for use in modeller.
    template_ids = []
    for (pdb, chain) in templates:
        template_ids.append(pdb + chain)

        src = '/home/modeller/databases/wwpdb/%s/pdb%s.ent.gz' % (pdb[1:3], pdb)
        dst = pdb + '.pdb.gz'

        if os.path.exists(dst):
            continue

        if os.path.exists(src):
            shutil.copy(src, dst)
            subprocess.check_call(['gzip', '-df', dst])

    # Generate the alignment file containing the full-length query sequence
    # and alignments to one or more template structures.
    alignment_file = 'alignment.pir'
    with open(alignment_file, 'w') as file:
        alignment = req.alignments[0]
        params = { 'query_id'    : query,
                   'query_start' : alignment.query_start,
                   'query_stop'  : alignment.query_stop,
                   'query_align' : alignment.query_align }

        file.write('%s\n' % query_alignment.safe_substitute(params))

        for (alignment, templ_id) in zip(req.alignments, templates):
            params = { 'templ_id'    : ''.join(templ_id),
                       'templ_pdb'   : alignment.templ_pdb + '.pdb',
                       'templ_chain' : alignment.templ_chain,
                       'templ_start' : alignment.templ_start,
                       'templ_stop'  : alignment.templ_stop,
                       'templ_align' : alignment.templ_align }

            file.write('%s\n' % templ_alignment.safe_substitute(params))

    # Run modeler
    modeller.log.verbose()

    env = modeller.environ()
    env.io.atom_files_directory = ['.']
    a = automodel(env,
                  alnfile = alignment_file,
                  knowns = template_ids,
                  sequence = query,
                  assess_methods = (DOPE, GA341))

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

    os.chdir(curr_dir)
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
        
