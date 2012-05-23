#include "util.h"

#include <boost/algorithm/string/regex.hpp>
#include <glog/logging.h>

#include <fstream>
#include <string>
#include <vector>

namespace hmmer {

void write_contents(const char* filename, const char* msg) {
  CHECK_NOTNULL(filename);
  CHECK_NOTNULL(msg);

  std::ofstream out(filename);
  CHECK(out.good());

  out << *msg;
  out.close();
}

void tokenize(const std::string& line,
              const std::string& expr,
              std::vector<std::string>* tokens) {
  CHECK_NOTNULL(tokens);
  tokens->clear();
  boost::regex pattern(expr);
  boost::algorithm::split_regex(*tokens, line, pattern);
}

}  // namespace hmmer
