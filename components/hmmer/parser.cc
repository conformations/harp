#include "parser.h"
#include "harp.pb.h"
#include "str_util.h"

#include <boost/algorithm/string.hpp>
#include <boost/algorithm/string/predicate.hpp>
#include <boost/algorithm/string/replace.hpp>
#include <boost/algorithm/string/trim.hpp>
#include <boost/lexical_cast.hpp>
#include <gflags/gflags.h>
#include <glog/logging.h>
#include <re2/re2.h>

#include <fstream>
#include <string>
#include <vector>

DEFINE_double(conf_delta, 0.1, "Candidate alignments must be within x% of top-ranked alignment");
DEFINE_double(cov_min, 0.9, "Candidate alignments must cover at least x% of the query sequence");

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
        parse_block(req->sequence(), block, alignment);
        block.clear();
      }
    }

    block.push_back(line);
  }

  // Parse the final block
  Alignment* alignment = req->add_alignments();
  alignment->set_rank(++rank);
  parse_block(req->sequence(), block, alignment);

  // Remove alignments that cover less than x% of the query sequence and those
  // whose confidence is less than y% of the top-ranked hit
  if (req->alignments_size()) {
    const double conf_threshold = (1 - FLAGS_conf_delta) * req->alignments(0).confidence();
    const double cov_threshold = FLAGS_cov_min;

    google::protobuf::RepeatedPtrField<Alignment>* alignments = req->mutable_alignments();

    for (int i = alignments->size() - 1; i >= 0; --i) {
      const Alignment& align = alignments->Get(i);

      // Because protobuf does not provide the ability to remove arbitrary
      // elements from a RepeatedField, we use a combination of SwapElements()
      // and RemoveLast()
      if (align.confidence() < conf_threshold || align.coverage() < cov_threshold) {
        alignments->SwapElements(i, alignments->size() - 1);
        alignments->RemoveLast();
      }
    }
  }

  // Close the file handle
  file.close();
}

void Parser::parse_block(const string& sequence, const vector<string>& block, Alignment* alignment) const {
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
  parse_line(block[qi], QUERY, &query);
  parse_line(block[ti], TEMPL, &templ);

  double coverage = static_cast<double>(query.stop - query.start + 1) / sequence.length();

  // Update alignment metadata
  alignment->set_source("hmmer");
  alignment->set_confidence(bits);
  alignment->set_coverage(coverage);

  // Extend the query alignment so that it contains the complete sequence,
  // padding the template alignment as necessary
  string leading  = sequence.substr(0, query.start - 1);
  string trailing = sequence.substr(query.stop);
  query.start = 1;
  query.stop  = sequence.length();
  query.align = leading + query.align + trailing;

  string leading_gaps(leading.length(), '-');
  string trailing_gaps(trailing.length(), '-');
  templ.align = leading_gaps + templ.align + trailing_gaps;

  // Update query alignment
  alignment->set_query_align(query.align);
  alignment->set_query_start(query.start);
  alignment->set_query_stop(query.stop);

  // Update template alignment
  alignment->set_templ_pdb(templ.pdb);
  alignment->set_templ_chain(templ.chain);
  alignment->set_templ_align(templ.align);
  alignment->set_templ_start(templ.start);
  alignment->set_templ_stop(templ.stop);
}

void Parser::parse_line(const string& line, LineType type, Entry* entry) const {
  CHECK_NOTNULL(entry);

  vector<string> tokens;
  tokenize(line, "\\s+", &tokens);
  CHECK(tokens.size() == 4) << "Incorrect number of tokens: " << line;

  entry->align = tokens[2];
  entry->start = boost::lexical_cast<int>(tokens[1]);
  entry->stop  = boost::lexical_cast<int>(tokens[3]);

  // Standardize the alignment format
  boost::replace_all(entry->align, ".", "-");
  boost::to_upper(entry->align);
  boost::trim(entry->align);

  // Retrieve PDB id and chain from template alignments
  if (type == TEMPL) {
    entry->pdb = tokens[0].substr(0, 4);
    entry->chain = tokens[0].substr(4, 1);

    boost::to_lower(entry->pdb);
    boost::to_upper(entry->chain);
  }
}

}  // namespace hmmer
