#include "harp.pb.h"
#include "proto_util.h"
#include "zmq_util.h"

#include <gflags/gflags.h>
#include <glog/logging.h>
#include <zmq.hpp>

#include <exception>
#include <iostream>
#include <string>

DEFINE_string(in, "tcp://localhost:8002", "Incoming socket");
DEFINE_int32(io_threads, 1, "Number of threads dedicated to I/O operations");

using namespace std;

int main(int argc, char* argv[]) {
  google::ParseCommandLineFlags(&argc, &argv, true);
  google::InitGoogleLogging(argv[0]);

  zmq::context_t context(FLAGS_io_threads);
  zmq::socket_t pull(context, ZMQ_PULL);

  try {
    pull.connect(FLAGS_in.c_str());
  } catch (std::exception& e) {
    LOG(FATAL) << "Failed to connect inbound socket: " << FLAGS_in << std::endl;
  }

  while (true) {
    string sender_uid = s_recv(pull);

    HarpResponse rep;
    CHECK(proto_recv(&rep, &pull));
    proto_show(rep, &cout);
  }
}
