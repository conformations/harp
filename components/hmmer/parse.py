import gflags
import re

FLAGS = gflags.FLAGS
gflags.DEFINE_float('coverage_min', 0.8, 'Candidate alignments must cover at least x% of the query sequence')
gflags.DEFINE_float('confidence_delta', 0.1, 'Candidate alignments must be within x% of top-ranked alignment')

# Enumeration type used during parsing to signify that the line to be parsed
# contains either the query sequence or a template sequence
QUERY = 0
TEMPL = 1

def parse_line(line, type):
    line = line.strip()
    tokens = re.split('\\s+', line)
    assert len(tokens) == 4

    start = int(tokens[1])
    stop  = int(tokens[3])

    alignment = tokens[2].strip()
    alignment = alignment.upper()
    alignment = alignment.replace('.', '-')

    pdb = None
    chain = None

    if type == TEMPL:
        id = tokens[0]
        pdb = id[0:4].lower()
        chain = id[4:5].upper()

    return (pdb, chain, alignment, start, stop)


def parse_block(sequence, block, alignment):
    # Indices of query and template sequences in `block`
    qi = None
    ti = None

    # Length-independent alignment confidence measure
    bits = None

    for (i, line) in enumerate(block):
        line = line.strip()
        if line.startswith('== domain'):
            qi = i + 1
            ti = i + 3

            match = re.search('(-?\\d+\\.\\d+) bits', line)
            if match:
                bits = float(match.groups()[0])

            break

    assert(qi)
    assert(ti)
    assert(bits)

    qpdb, qchain, qalign, qstart, qstop = parse_line(block[qi], QUERY)
    tpdb, tchain, talign, tstart, tstop = parse_line(block[ti], TEMPL)

    # Update alignment metadata
    alignment.method = 'hmmer'
    alignment.confidence = bits

    # Update query alignment
    alignment.query_align = qalign
    alignment.query_start = qstart
    alignment.query_stop  = qstop

    # Update template alignment
    alignment.templ_pdb   = tpdb
    alignment.templ_chain = tchain
    alignment.templ_align = talign
    alignment.templ_start = tstart
    alignment.templ_stop  = tstop


def parse(output, rep):
    with open(output) as file:
        # Fast-forward the stream to the first line matching the given prefix
        for line in file:
            line = line.strip()
            if line.startswith('Domain annotation for each sequence (and alignments):'):
                break

        block = []

        # Partition the contents of `output` into alignment blocks delimited by '>>'
        # and EOF. When the next block is encountered, the current one is parsed and
        # added to `rep`.
        sequence = rep.sequence

        for line in file:
            line = line.strip()

            if line.startswith('>>'):
                if block:
                    alignment = rep.alignments.add()
                    parse_block(sequence, block, alignment)
                    del block[:]

            block.append(line)

        # Parse the final block
        alignment = rep.alignments.add()
        parse_block(sequence, block, alignment)

    # Remove alignments whose confidence is below some delta of the top-ranked
    # alignment. Because protobuf does not provide the ability to remove specific
    # elements from a repeated field, we use del alignment[x].
    if rep.alignments:
        conf_min = (1 - FLAGS.confidence_delta) * rep.alignments[0].confidence

        n = len(rep.alignments)
        for i in range(n - 1, -1, -1):
            conf = rep.alignments[i].confidence
            cov  = (rep.alignments[i].templ_stop - rep.alignments[i].templ_start + 1) / float(len(rep.sequence))

            if conf < conf_min or cov < FLAGS.coverage_min:
                del rep.alignments[i]
