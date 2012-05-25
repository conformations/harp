#! /usr/bin/env python
import harp_pb2
from proto_util import *
import zmq

import argparse
import os
import os.path
import re
import string
import subprocess
import sys
import tempfile

hmmer_cmd = string.Template('$exe --notextw -o $out $fasta $db')

QUERY = 0
TEMPL = 1

def parse_line(line, type):
    '''Parses a hmmer alignment line into its constituent pieces'''
    line = line.strip()
    tokens = re.split('\\s+', line)
    assert len(tokens) == 4

    start_pos = int(tokens[1])
    stop_pos  = int(tokens[3])

    alignment = tokens[2]
    alignment = alignment.upper()
    alignment = alignment.replace('.', '-')

    pdb = None
    chain = None

    if type == TEMPL:
        tokens = tokens[0].split('|')
        assert len(tokens) == 5

        pdb = tokens[-2].lower()
        chain = tokens[-1].upper()

    return (pdb, chain, alignment, start_pos, stop_pos)


def parse_block(block, alignment):
    # Indices of query and template sequences in `block`
    qi = None
    ti = None

    # Length-independent alignment confidence measure
    bits = None

    for (i, line) in enumerate(block):
        line = line.strip()
        if line.startswith('== domain'):
            qi = i + 1
            ti = i + 3

            match = re.search('(-?\\d+\\.\\d+) bits', line)
            if match:
                bits = float(match.groups()[0])

            break

    assert(qi)
    assert(ti)
    assert(bits)

    qpdb, qchain, qalign, qstart, qstop = parse_line(block[qi], QUERY)
    tpdb, tchain, talign, tstart, tstop = parse_line(block[ti], TEMPL)

    # Update alignment metadata
    alignment.source = 'hmmer'
    alignment.confidence = bits

    # Update query alignment
    alignment.query_align = qalign
    alignment.query_start = qstart
    alignment.query_stop  = qstop

    # Update template alignment
    alignment.templ_pdb = tpdb
    alignment.templ_chain = tchain
    alignment.templ_align = talign
    alignment.templ_start = tstart
    alignment.templ_stop  = tstop


def parse(output, rep):
    '''Partitions the contents of `output` into a series of alignment blocks,
    which are subsequently parsed by `parse_block`. Populates the alignment
    field of `req` with the result. Alignments are filtered according to the
    confidence of the top-ranked hit.

    t = confidence of top-ranked alignment * X
    for a in alignments:
      if confidence(a) < t:
        remove a

    '''
    with open(output) as file:
        # Fast-forward the stream to the first line matching the given prefix
        for line in file:
            line = line.strip()
            if line.startswith('Domain annotation for each sequence (and alignments):'):
                break

        rank = 0
        block = []

        # Partition the contents of `output` into alignment blocks delimited by '>>'
        # and EOF. When the next block is encountered, the current one is parsed and
        # added to `rep`.
        for line in file:
            line = line.strip()

            if line.startswith('>>'):
                if block:
                    rank += 1
                    alignment = rep.alignments.add()
                    alignment.rank = rank
                    parse_block(block, alignment)
                    del block[:]

            block.append(line)

        # Parse the final block
        rank += 1
        alignment = rep.alignments.add()
        alignment.rank = rank
        parse_block(block, alignment)

    # Remove alignments whose confidence is below some delta of the top-ranked
    # alignment. Because protobuf does not provide the ability to remove specific
    # elements from a repeated field, we use del alignment[x].
    if rep.alignments:
        threshold = rep.alignments[0].confidence * 0.9

        n = len(rep.alignments)
        for i in range(n - 1, -1, -1):
            if rep.alignments[i].confidence < threshold:
                del rep.alignments[i]


def process(options, req, rep):
    '''Processes a single request to the server, storing the result in `rep`'''
    # Create temporary files to store the input/output from hmmer.
    # Caller is responsible for deleting them.
    (handle, tmp_in) = tempfile.mkstemp()
    (handle, tmp_out) = tempfile.mkstemp()

    # Write the fasta sequence to file
    with open(tmp_in, 'w') as file:
        file.write('%s\n' % req.sequence)

    params = { 'exe' : options['exe'], 'db' : options['db'], 'fasta' : tmp_in, 'out' : tmp_out }
    output = subprocess.check_output(hmmer_cmd.safe_substitute(params).split())

    parse(tmp_out, rep)
    rep.sequence = req.sequence
    rep.recipient = req.recipient
    rep.identifier = req.identifier

    try:
        os.remove(tmp_in)
        os.remove(tmp_out)
    except:
        sys.stderr.write('Failed to remove one or more temporary files: %s, %s' % (tmp_in, tmp_out))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--in',  default = 'tcp://localhost:8001', help = 'Incoming socket')
    parser.add_argument('--out', default = 'tcp://localhost:8002', help = 'Outgoing socket')
    parser.add_argument('--exe', default = '/usr/local/bin/phmmer', help = 'Absolute path to hmmer executable')
    parser.add_argument('--db', default = '/home/hmmer/databases/pdbaa', help = 'Absolute path to hmmer database')
    options = vars(parser.parse_args())

    # validate inputs
    assert os.path.exists(options['exe'])
    assert os.path.exists(options['db'])

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
        req = harp_pb2.HarpRequest()
        rep = harp_pb2.ModelingRequest()

        proto_recv(fe, req)
        process(options, req, rep)
        proto_send(be, rep)
