// A collection of utility functions used by hmmer.
// @author Christopher Miles (cmiles@uw.edu)

#ifndef HARP_COMPONENTS_HMMER_UTIL_H_
#define HARP_COMPONENTS_HMMER_UTIL_H_

#include <string>
#include <vector>

namespace hmmer {

// Opens `filename` for writing and replaces its contents with `msg`.
void write_contents(const char* filename, const char* msg);

// Populates tokens with the result of splitting line by expr
void tokenize(const std::string& line,
              const std::string& regex,
              std::vector<std::string>* tokens);

}  // namespace hmmer

#endif  // HARP_COMPONENTS_HMMER_UTIL_H_
