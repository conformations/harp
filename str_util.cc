#include "str_util.h"

#include <boost/algorithm/string/regex.hpp>
#include <glog/logging.h>

#include <fstream>
#include <string>
#include <vector>

void write_contents(const char* filename, const std::string& msg) {
  CHECK_NOTNULL(filename);

  std::ofstream out(filename);
  CHECK(out.good());

  out << msg;
  out.close();
}

void read_contents(const char* filename, std::string* msg) {
  CHECK_NOTNULL(filename);
  CHECK_NOTNULL(msg);

  std::ifstream file(filename);
  CHECK(file.good());

  std::string line;
  while (file.good()) {
    getline(file, line);
    *msg += line;
  }

  file.close();
}

void tokenize(const std::string& line,
              const std::string& expr,
              std::vector<std::string>* tokens) {
  CHECK_NOTNULL(tokens);
  tokens->clear();
  boost::regex pattern(expr);
  boost::algorithm::split_regex(*tokens, line, pattern);
}

