// A collection of functions for parsing hmmer output.
// @author Christopher Miles (cmiles@uw.edu)

#ifndef HARP_COMPONENTS_HMMER_PARSER_H_
#define HARP_COMPONENTS_HMMER_PARSER_H_

#include "harp.pb.h"
#include <string>
#include <vector>

namespace hmmer {

class Parser {
  // Simple container for storing information for one entry of an alignment
  typedef struct {
    std::string name;
    std::string align;
    int pos_start;
    int pos_stop;
  } Entry;

 public:
  // Partitions the contents of `filename` into a series of alignment blocks,
  // which are subsequently parsed by `parse_block`. Populates the alignment
  // fields of `req` with the result.
  void parse(const char* filename, ModelingRequest* req) const;

 protected:
  // Parses the contents of a single alignment block into its constituent pieces
  // and writes the results to `alignment`.
  void parse_block(const std::vector<std::string>& block, Alignment* alignment) const;

  // Parses a single alignment entry into its constituent pieces. Assumes that `line`
  // has had leading and trailing whitespace removed.
  void parse_line(const std::string& line, Entry* entry) const;
};

}  // namespace hmmer

#endif  // HARP_COMPONENTS_HMMER_PARSER_H_
