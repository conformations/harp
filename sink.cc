#include "harp.pb.h"
#include "proto_util.h"
#include "zmq_util.h"

#include <gflags/gflags.h>
#include <glog/logging.h>
#include <zmq.hpp>

#include <exception>
#include <iostream>

DEFINE_string(incoming, "tcp://localhost:8002", "Incoming socket");

int main(int argc, char* argv[]) {
  google::ParseCommandLineFlags(&argc, &argv, true);
  google::InitGoogleLogging(argv[0]);

  zmq::context_t context(1);
  zmq::socket_t pull(context, ZMQ_PULL);

  try {
    pull.connect(FLAGS_incoming.c_str());
  } catch (std::exception& e) {
    LOG(FATAL) << "Failed to connect inbound socket: " << FLAGS_incoming << std::endl;
  }

  while (true) {
    s_recv(pull);  // sender uid

    HarpResponse rep;
    CHECK(proto_recv(&rep, &pull));
    proto_show(rep, &std::cout);
  }
}
