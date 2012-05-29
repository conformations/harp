// A collection of functions for parsing hmmer output.
// @author Christopher Miles (cmiles@uw.edu)

#ifndef HARP_COMPONENTS_HMMER_PARSER_H_
#define HARP_COMPONENTS_HMMER_PARSER_H_

#include "harp.pb.h"
#include <string>
#include <vector>

namespace hmmer {

class Parser {
  enum LineType { QUERY, TEMPL };

  // Simple container for storing data about one entry of an alignment
  typedef struct {
    std::string pdb;
    std::string chain;
    std::string align;
    int start;
    int stop;
  } Entry;

 public:
  // Partitions the contents of `filename` into a series of blocks, which are
  // subsequently parsed by `parse_block()`. Populates the alignment fields of
  // `req` with the result. Filters alignments that cover less than x% of the
  // query sequence and those whose confidence is less than y% of the top-ranked
  // hit.
  //
  // At the time this method is called, `req` must contain the query sequence.
  void parse(const char* filename, ModelingRequest* req) const;

 protected:
  // Parses the contents of a single alignment block into its constituent pieces
  // and writes the results to `alignment`. The full-length query sequence is
  // needed to ensure that the resulting alignments are complete.
  void parse_block(const std::string& sequence,
		   const std::vector<std::string>& block,
		   Alignment* alignment) const;

  // Parses a single alignment entry into its constituent pieces. Assumes that `line`
  // has had leading and trailing whitespace removed.
  void parse_line(const std::string& line, LineType type, Entry* entry) const;
};

}  // namespace hmmer

#endif  // HARP_COMPONENTS_HMMER_PARSER_H_
