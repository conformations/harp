// A collection of high-level functions for sending and receiving protocol
// buffers over ZeroMQ sockets.
//
// @author Christopher Miles (cmiles@uw.edu)

#ifndef PROTO_UTIL_H_
#define PROTO_UTIL_H_

#include "zmq_util.h"

#include <glog/logging.h>
#include <google/protobuf/message.h>
#include <google/protobuf/text_format.h>
#include <snappy.h>
#include <zmq.hpp>

#include <iostream>
#include <string>

bool proto_send(const google::protobuf::Message& r, zmq::socket_t* socket) {
  CHECK_NOTNULL(socket);

  std::string m;
  google::protobuf::TextFormat::PrintToString(r, &m);

  std::string n;
  snappy::Compress(m.data(), m.size(), &n);
  return s_send(*socket, n);
}

bool proto_recv(google::protobuf::Message* r, zmq::socket_t* socket) {
  CHECK_NOTNULL(r);
  CHECK_NOTNULL(socket);

  std::string m = s_recv(*socket);
  std::string n;
  snappy::Uncompress(m.data(), m.size(), &n);
  return google::protobuf::TextFormat::ParseFromString(n, r);
}

void proto_show(const google::protobuf::Message& r, std::ostream* out) {
  CHECK_NOTNULL(out);
  
  std::string m;
  google::protobuf::TextFormat::PrintToString(r, &m);
  (*out) << m << std::endl;
}

#endif  // PROTO_UTIL_H_
