#! /usr/bin/env python
from alignment import *
from proto_util import *
from parse import parse
import harp_pb2
import gflags
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
gflags.DEFINE_string('exe', '/usr/local/bin/phmmer', 'Absolute path to hmmer executable')
gflags.DEFINE_string('db', '/home/hmmer/databases/pdbaa', 'Absolute path to hmmer database')

hmmer_cmd = string.Template('$exe --notextw -o $out $fasta $db')
fetch_cmd = string.Template('/home/hmmer/src/cm_scripts/bin/get_pdb.py $pdb $chain')
match_cmd = string.Template('/home/hmmer/src/rosetta/rosetta_source/bin/fix_alignment_to_match_pdb.default.linuxgccrelease -database /home/hmmer/src/rosetta/rosetta_database -in:file:alignment $align_in -out:file:alignment $align_out -cm:aln_format grishin -in:file:template_pdb $templates')

def update_alignments(alignments, filename):
    # Partitions the Grishin-format alignment into blocks delimited by --
    with open(filename) as file:
        blocks, block = [], []

        for line in file:
            line = line.strip()
            if len(line) == 0:
                continue

            if line.startswith('--'):
                blocks.append(block)
                block = []
            else:
                block.append(line)

    for (alignment, block) in zip(alignments, blocks):
        query_line = block[-2]
        templ_line = block[-1]

        qstart, qalign = query_line.split()
        tstart, talign = templ_line.split()
        qstart = int(qstart)
        tstart = int(tstart)

        alignment.query_start = qstart + 1
        alignment.query_align = qalign

        alignment.templ_start = tstart + 1
        alignment.templ_align = talign
        alignment.templ_stop  = len(filter(lambda x: x != '-', talign))


def fix_alignments(alignments):
    if not alignments:
        return

    curr_dir = os.getcwd()
    work_dir = tempfile.mkdtemp()
    os.chdir(work_dir)

    # Convert protobuf to grishin format
    alignment_in  = 'alignment.filt'
    alignment_out = 'alignment.renum.filt'
    to_grishin(alignments, alignment_in, COUNT_FROM_1)

    # Retrieve template structures, discarding alignments for which the
    # process was unsuccessful. At the conclusion of this block, `templates`
    # will contain absolute paths to each valid template structure.
    templates = []

    for (i, alignment) in enumerate(alignments):
        params = { 'pdb' : alignment.templ_pdb, 'chain' : alignment.templ_chain }
        subprocess.check_call(fetch_cmd.safe_substitute(params).split())

        # Verify that the template structure was successfully retrieved.
        # If unsuccessful, remove the template from `alignments`.
        filename = os.path.abspath(alignment.templ_pdb + alignment.templ_chain + '.pdb')

        if not os.path.exists(filename):
            print 'Error retrieving pdb=%s, chain=%s' % (alignment.templ_pdb, alignment.templ_chain)
            del alignments[i]
        else:
            templates.append(filename)

    # Update alignment numbering to match template
    params = {
        'align_in' : alignment_in,
        'align_out' : alignment_out,
        'templates' : ' '.join(templates)
        }

    subprocess.check_call(match_cmd.safe_substitute(params).split())
    update_alignments(alignments, alignment_out)

    # Serialize template structures to proto
    for (alignment, template) in zip(alignments, templates):
        coords = ''
        with open(template) as file:
            for line in file:
                coords += line

        alignment.templ_structure = coords

    os.chdir(curr_dir)
    shutil.rmtree(work_dir)


def process(req, rep):
    (handle, tmp_in)  = tempfile.mkstemp()
    (handle, tmp_out) = tempfile.mkstemp()

    # Update carry-over parameters
    rep.sequence = req.sequence
    rep.recipient = req.recipient
    rep.identifier = req.identifier

    #  Write query sequence to file in FASTA format
    with open(tmp_in, 'w') as file:
        file.write('> x\n')
        file.write('%s\n' % req.sequence)

    params = { 'exe' : FLAGS.exe, 'db' : FLAGS.db, 'fasta' : tmp_in, 'out' : tmp_out }
    subprocess.check_call(hmmer_cmd.safe_substitute(params).split())

    parse(tmp_out, rep)
    fix_alignments(rep.alignments)

    try:
        os.remove(tmp_in)
        os.remove(tmp_out)
    except:
        sys.stderr.write('Failed to remove one or more temporary files: %s, %s' % (tmp_in, tmp_out))


if __name__ == '__main__':
    try:
        sys.argv = FLAGS(sys.argv)
    except gflags.FlagsError, e:
        print '%s\\nUsage: %s ARGS\\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    # Validate inputs
    assert os.path.exists(FLAGS.exe)
    assert os.path.exists(FLAGS.db)

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
        req = harp_pb2.HarpRequest()
        rep = harp_pb2.ModelingRequest()

        proto_recv(fe, req)
        process(req, rep)
        proto_send(be, rep)
