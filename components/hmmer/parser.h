// A collection of functions for parsing hmmer output.
// @author Christopher Miles (cmiles@uw.edu)

#ifndef HARP_COMPONENTS_HMMER_PARSER_H_
#define HARP_COMPONENTS_HMMER_PARSER_H_

#include "harp.pb.h"
#include <string>

namespace hmmer {

class Parser {
 public:
  // Populates the alignment field of `req` by parsing the contents of `filename`
  void parse(const char* filename, ModelingRequest* req) const;

 protected:
  void parse_block(const std::string& block, Alignment* alignment) const;
  void parse_line(const std::string& line, Alignment* alignment) const;
};

}  // namespace hmmer

#endif  // HARP_COMPONENTS_HMMER_PARSER_H_
