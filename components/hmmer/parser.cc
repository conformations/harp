#include "parser.h"
#include "harp.pb.h"
#include "util.h"

#include <boost/algorithm/string.hpp>
#include <boost/algorithm/string/predicate.hpp>
#include <boost/algorithm/string/replace.hpp>
#include <boost/algorithm/string/trim.hpp>
#include <boost/lexical_cast.hpp>
#include <glog/logging.h>
#include <re2/re2.h>

#include <fstream>
#include <string>
#include <vector>

namespace hmmer {

using std::string;
using std::vector;

void Parser::parse(char const* filename, ModelingRequest* req) const {
  CHECK_NOTNULL(filename);
  CHECK_NOTNULL(req);

  std::ifstream file(filename);
  CHECK(file.is_open());

  // Fast-forward the stream to the first line matching the given prefix
  string line;
  while (file.good()) {
    getline(file, line);
    boost::trim(line);

    if (boost::starts_with(line, "Domain annotation for each sequence (and alignments):")) {
      break;
    }
  }

  int rank = 0;
  vector<string> block;

  // Partition the contents of `filename` into alignment blocks delimited by '>>'
  // and EOF. When the next block is encountered, the current block is parsed and
  // added to `req`.
  while (file.good()) {
    getline(file, line);
    boost::trim(line);

    if (boost::starts_with(line, ">>")) {
      if (block.size()) {
        Alignment* alignment = req->add_alignments();
        alignment->set_rank(++rank);
        parse_block(block, alignment);
        block.clear();
      }
    }

    block.push_back(line);
  }

  // Parse the final block
  Alignment* alignment = req->add_alignments();
  alignment->set_rank(++rank);
  parse_block(block, alignment);

  // Remove alignments whose confidence is below some delta of the top-ranked
  // alignment. Because protobuf does not provide the ability to remove specific
  // elements from a repeated field, we use SwapElements() + RemoveLast().
  if (req->alignments_size()) {
    double threshold = req->alignments(0).confidence() * 0.9;
    google::protobuf::RepeatedPtrField<Alignment>* alignments = req->mutable_alignments();

    for (int i = alignments->size() - 1; i >= 0; --i) {
      if (alignments->Get(i).confidence() < threshold) {
        alignments->SwapElements(i, alignments->size() - 1);
        alignments->RemoveLast();
      }
    }
  }

  // Close the file handle
  file.close();
}

void Parser::parse_block(const vector<string>& block, Alignment* alignment) const {
  CHECK_NOTNULL(alignment);

  // Indices of query and template sequences in `block`
  size_t qi = -1;
  size_t ti = -1;

  // Length-independent alignment confidence
  double bits = -1;

  for (size_t i = 0; i < block.size(); ++i) {
    string line = block[i];
    boost::trim(line);

    if (boost::starts_with(line, "== domain")) {
      qi = i + 1;
      ti = i + 3;

      CHECK(RE2::PartialMatch(line, "(-?\\d+\\.\\d+) bits", &bits));
      break;
    }
  }

  CHECK(qi != -1);
  CHECK(ti != -1);

  Entry query, templ;
  parse_line(block[qi], &query);
  parse_line(block[ti], &templ);

  // Update alignment metadata
  alignment->set_source("hmmer");
  alignment->set_confidence(bits);

  // Update query alignment
  alignment->set_query_align(query.align);
  alignment->set_query_start(query.pos_start);
  alignment->set_query_stop(query.pos_stop);

  // Update template alignment
  alignment->set_template_pdb(templ.name);
  alignment->set_templ_align(templ.align);
  alignment->set_templ_start(templ.pos_start);
  alignment->set_templ_stop(templ.pos_stop);
}

void Parser::parse_line(const string& line, Entry* entry) const {
  CHECK_NOTNULL(entry);

  vector<string> tokens;
  tokenize(line, "\\s+", &tokens);
  CHECK(tokens.size() == 4) << "Incorrect number of columns in line: " << line;

  entry->name  = tokens[0];
  entry->align = tokens[2];
  entry->pos_start = boost::lexical_cast<int>(tokens[1]);
  entry->pos_stop  = boost::lexical_cast<int>(tokens[3]);

  // Standardize the alignment format
  boost::replace_all(entry->align, ".", "-");
  boost::to_upper(entry->align);
}

}  // namespace hmmer
