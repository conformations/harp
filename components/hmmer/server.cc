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
#include <string>

DEFINE_string(incoming, "tcp://localhost:8001", "Incoming socket");
DEFINE_string(outgoing, "tcp://localhost:8002", "Outgoing socket");

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

  // Create temporary files to store the input/output to hmmer. Use these to
  // populate the remaining values in the template dictionary.
  char tmp_in [L_tmpnam];
  char tmp_out[L_tmpnam];
  tmpnam(tmp_in);
  tmpnam(tmp_out);

  tmpl->SetValue("IN", tmp_in);
  tmpl->SetValue("OUT", tmp_out);

  // Write the query sequence to file
  write_contents(tmp_in, "> x\n" + req.sequence());

  string cmd;
  ctemplate::ExpandTemplate(FLAGS_tpl, ctemplate::STRIP_WHITESPACE, tmpl, &cmd);
  std::system(cmd.c_str());

  hmmer::Parser parser;
  rep->set_sequence(req.sequence());
  rep->set_recipient(req.recipient());
  rep->set_identifier(req.identifier());
  parser.parse(tmp_out, rep);

  CHECK(std::remove(tmp_in)  == 0) << "Failed to remove temporary file " << tmp_in;
  CHECK(std::remove(tmp_out) == 0) << "Failed to remove temporary file " << tmp_out;
}

int main(int argc, char* argv[]) {
  google::ParseCommandLineFlags(&argc, &argv, true);
  google::InitGoogleLogging(argv[0]);

  // Verify that the version of the protocol buffer library that we linked
  // against is compatible with the version of the headers we compiled against
  GOOGLE_PROTOBUF_VERIFY_VERSION;

  zmq::context_t context(1);
  zmq::socket_t fe(context, ZMQ_PULL);
  zmq::socket_t be(context, ZMQ_PUSH);

  try {
    fe.connect(FLAGS_incoming.c_str());
  } catch (std::exception& e) {
    LOG(FATAL) << "Failed to connect incoming socket: " << FLAGS_incoming;
  }

  try {
    be.connect(FLAGS_outgoing.c_str());
  } catch (std::exception& e) {
    LOG(FATAL) << "Failed to connect outgoing socket: " << FLAGS_outgoing;
  }

  // Populate the template dictionary with as much information as we have
  // at this point. Callers are responsible for setting IN and OUT params.
  TemplateDictionary tmpl("hmmer");
  tmpl.SetValue("EXE", FLAGS_exe);
  tmpl.SetValue("DB", FLAGS_db);

  while (true) {
    s_recv(fe);  // sender's uid

    HarpRequest req;
    CHECK(proto_recv(&req, &fe));

    ModelingRequest rep;
    process(req, &rep, &tmpl);
    CHECK(proto_send(rep, &be));
  }
}
