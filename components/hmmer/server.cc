#include "harp.pb.h"
#include "parser.h"
#include "proto_util.h"
#include "str_util.h"
#include "zmq_util.h"

#include <ctemplate/template.h>
#include <gflags/gflags.h>
#include <glog/logging.h>
#include <zmq.hpp>

#include <cstdio>
#include <exception>
#include <iostream>
#include <string>

DEFINE_string(in, "tcp://localhost:8001", "Incoming socket");
DEFINE_string(out, "tcp://localhost:8002", "Outgoing socket");
DEFINE_int32(io_threads, 1, "Number of threads dedicated to I/O operations");

// Absolute paths to hmmer executable and sequence database
DEFINE_string(exe, "/usr/local/bin/phmmer", "hmmer executable");
DEFINE_string(db, "/home/hmmer/databases/pdbaa", "hmmer database");

// Absolute path to hmmer execution template
DEFINE_string(tpl, "/home/hmmer/conf/hmmer.tpl", "hmmer template");

using ctemplate::TemplateDictionary;
using std::string;

// Processes a single request to the server
void process(const HarpRequest& req, ModelingRequest* rep, TemplateDictionary* tmpl) {
  CHECK_NOTNULL(rep);
  CHECK_NOTNULL(tmpl);

  // Create temporary files to store the input (tmp_in) to and output (tmp_out) from hmmer.
  // Populate the remaining values in the template dictionary.
  char tmp_in [L_tmpnam];
  char tmp_out[L_tmpnam];
  tmpnam(tmp_in);
  tmpnam(tmp_out);

  tmpl->SetValue("IN", tmp_in);
  tmpl->SetValue("OUT", tmp_out);

  // Write the query sequence to file
  write_contents(tmp_in, req.sequence());

  string cmd;
  ctemplate::ExpandTemplate(FLAGS_tpl, ctemplate::STRIP_WHITESPACE, tmpl, &cmd);
  std::system(cmd.c_str());

  hmmer::Parser parser;
  parser.parse(tmp_out, rep);
  rep->set_sequence(req.sequence());
  rep->set_recipient(req.recipient());

  CHECK(std::remove(tmp_in)  == 0) << "Failed to remove temporary file " << tmp_in;
  CHECK(std::remove(tmp_out) == 0) << "Failed to remove temporary file " << tmp_out;
}

int main(int argc, char* argv[]) {
  google::ParseCommandLineFlags(&argc, &argv, true);
  google::InitGoogleLogging(argv[0]);

  // Verify that the version of the protocol buffer library that we linked
  // against is compatible with the version of the headers we compiled against
  GOOGLE_PROTOBUF_VERIFY_VERSION;

  zmq::context_t context(FLAGS_io_threads);
  zmq::socket_t fe(context, ZMQ_PULL);
  zmq::socket_t be(context, ZMQ_PUSH);

  try {
    fe.connect(FLAGS_in.c_str());
  } catch (std::exception& e) {
    LOG(FATAL) << "Failed to connect incoming socket: " << FLAGS_in << std::endl;
  }

  try {
    be.connect(FLAGS_out.c_str());
  } catch (std::exception& e) {
    LOG(FATAL) << "Failed to connect outgoing socket: " << FLAGS_out << std::endl;
  }

  // Populate the template dictionary with as much information as we have
  // at this point. Callers are responsible for setting IN and OUT params.
  TemplateDictionary tmpl("hmmer");
  tmpl.SetValue("EXE", FLAGS_exe);
  tmpl.SetValue("DB", FLAGS_db);

  while (true) {
    // sender's uid
    string uid = s_recv(fe);

    HarpRequest req;
    CHECK(proto_recv(&req, &fe));

    ModelingRequest rep;
    process(req, &rep, &tmpl);
    CHECK(proto_send(rep, &be));

    LOG(INFO) << "Identified " << rep.alignments_size() << " alignments "
              << "for sequence " << req.sequence()
              << std::endl;
  }
}
