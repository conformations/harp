#include "parser.h"
#include "harp.pb.h"

#include <boost/algorithm/string/predicate.hpp>
#include <boost/algorithm/string/trim.hpp>
#include <glog/logging.h>

#include <fstream>
#include <string>

namespace hmmer {

void Parser::parse(char const*, ModelingRequest*) const {}
void Parser::parse_block(const std::string& block, Alignment* alignment) const {}
void Parser::parse_line(const std::string& line, Alignment* alignment) const {}

}  // namespace hmmer
