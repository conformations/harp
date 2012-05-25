// A collection of utility functions used by hmmer.
// @author Christopher Miles (cmiles@uw.edu)

#ifndef HARP_STR_UTIL_H_
#define HARP_STR_UTIL_H_

#include <string>
#include <vector>

// Opens `filename` for writing and replaces its contents with `msg`
void write_contents(const char* filename, const std::string& msg);

// Writes the contents of `filename` into `msg`
void read_contents(const char* filename, std::string* msg);

// Populates tokens with the result of splitting line by expr
void tokenize(const std::string& line,
              const std::string& regex,
              std::vector<std::string>* tokens);

#endif  // HARP_STR_UTIL_H_
