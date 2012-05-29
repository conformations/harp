#include <gflags/gflags.h>
#include <glog/logging.h>
#include <zmq.hpp>

#include <exception>
#include <iostream>

DEFINE_string(incoming, "tcp://*:8000", "Incoming socket");
DEFINE_string(outgoing, "tcp://*:8001", "Outgoing socket");

int main (int argc, char *argv[]) {
  google::ParseCommandLineFlags(&argc, &argv, true);
  google::InitGoogleLogging(argv[0]);

  zmq::context_t context(1);
  zmq::socket_t fe(context, ZMQ_ROUTER);
  zmq::socket_t be(context, ZMQ_DEALER);

  try {
    fe.bind(FLAGS_incoming.c_str());
  } catch (std::exception& e) {
    LOG(FATAL) << "Failed to bind frontend socket: " << FLAGS_incoming << std::endl;
  }

  try {
    be.bind(FLAGS_outgoing.c_str());
  } catch (std::exception& e) {
    LOG(FATAL) << "Failed to bind backend socket: " << FLAGS_outgoing << std::endl;
  }

  zmq::device(ZMQ_QUEUE, fe, be);
}
