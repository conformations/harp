// A simple command line utility for submitting jobs to HARP.
// @author Christopher Miles (cmiles@uw.edu)

#include "harp.pb.h"
#include "proto_util.h"

#include <boost/algorithm/string/predicate.hpp>
#include <gflags/gflags.h>
#include <glog/logging.h>
#include <zmq.hpp>

#include <exception>
#include <fstream>
#include <map>
#include <string>

DEFINE_string(outgoing, "tcp://localhost:8000", "Outgoing socket");
DEFINE_string(fasta, "", "File containing the query sequence in FASTA format");
DEFINE_string(email, "", "Email address of recipient");

using namespace std;

void read_sequences(const string& filename, map<string, string>* sequences) {
  CHECK_NOTNULL(sequences);

  ifstream file(filename.c_str());
  CHECK(file.is_open());

  string line;
  string header, sequence;

  while (file.good()) {
    getline(file, line);

    if (boost::starts_with(line, ">")) {
      // Create a new block, writing the previous one (if it exists)
      if (sequence.length()) {
	(*sequences)[header] = sequence;
	sequence.clear();
      }

      header = line;
    } else {
	sequence += line;
    }
  }

  // Write the final block
  (*sequences)[header] = sequence;
  file.close();
}

int main(int argc, char* argv[]) {
  google::ParseCommandLineFlags(&argc, &argv, true);
  google::InitGoogleLogging(argv[0]);

  // Verify that the version of the protocol buffer library that we linked
  // against is compatible with the version of the headers we compiled against
  GOOGLE_PROTOBUF_VERIFY_VERSION;

  // Validate arguments
  CHECK(!FLAGS_email.empty()) << "Failed to provide required argument --email";
  CHECK(!FLAGS_fasta.empty()) << "Failed to provide required argument --fasta";

  zmq::context_t context(1);
  zmq::socket_t comp(context, ZMQ_PUSH);

  try {
    comp.connect(FLAGS_outgoing.c_str());
  } catch (exception& e) {
    LOG(FATAL) << "Failed to connect outbound socket: " << FLAGS_outgoing;
  }

  map<string, string> sequences;
  read_sequences(FLAGS_fasta, &sequences);

  for (map<string, string>::const_iterator i = sequences.begin(); i != sequences.end(); ++i) {
    const string& id  = i->first;
    const string& seq = i->second;

    HarpRequest req;
    req.set_sequence(seq);
    req.set_identifier(id);
    req.set_recipient(FLAGS_email);
    CHECK(proto_send(req, &comp));
  }
}
