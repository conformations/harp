#! /usr/bin/env python
from proto_util import *
import harp_pb2
import gflags
import zmq

import logging
import os
import os.path
import shutil
import string
import sys
import tempfile

FLAGS = gflags.FLAGS
gflags.DEFINE_string('incoming', 'tcp://localhost:8001', 'Incoming socket')
gflags.DEFINE_string('outgoing', 'tcp://localhost:8002', 'Outgoing socket')

gflags.DEFINE_string('rosetta_dir', '/home/hmmer/src/rosetta', 'Absolute path to rosetta directory')

relax_cmd = string.Template('$base_dir/rosetta_source/bin/relax.default.linuxgccrelease -database $base_dir/rosetta_database -in:file:s $pdb -relax:constrain_relax_to_start_coords -relax:coord_constrain_sidechains -relax:ramp_constraints false -ignore_unrecognized_res -use_input_sc -correct -ex1 -ex2 -no_his_his_pairE -no_optH false -flip_HNQ')


def process(req):
    curr_dir = os.getcwd()
    work_dir = tempfile.mkdtemp()

    os.chdir(work_dir)

    # Minimize each predicted structure
    for selection in req.selected:
        pdb_in  = 'm.pdb'
        pdb_out = 'm_0001.pdb'

        with open(pdb_in, 'w') as file:
            coords = selection.model
            file.write('%s\n' % coords)

        assert os.path.exists(pdb_in)
        params = { 'base_dir' : FLAGS.rosetta_dir, 'pdb' : pdb_in }
        os.system(relax_cmd.safe_substitute(params))
        assert os.path.exists(pdb_out)

        # Read relaxed coordinates
        coords = ''
        with open(pdb_out) as file:
            for line in file:
                coords += line

        selection.model = coords
        os.remove(pdb_in)
        os.remove(pdb_out)
        
    os.chdir(curr_dir)

    try:
        shutil.rmtree(work_dir)
    except:
        sys.stderr.write('Failed to remove temporary directory: %s' % work_dir)


if __name__ == '__main__':
    try:
        sys.argv = FLAGS(sys.argv)
    except gflags.FlagsError, e:
        print '%s\\nUsage: %s ARGS\\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    # Setup logging
    logging.basicConfig(filename = 'minimize_server.log',
                        format = '%(asctime)-15s %(message)s',
                        level = logging.INFO)

    logger = logging.getLogger('minimize_server')

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
        req = harp_pb2.HarpResponse()

        try:
            proto_recv(fe, req)

            try:
                process(req)
                proto_send(be, req)
            except Exception as e:
                logger.error('Error occurred while processing request')
                logger.error(e)

        except Exception as e:
            logger.error('Failed to parse incoming message; expected HarpResponse')
            logger.error(e)
