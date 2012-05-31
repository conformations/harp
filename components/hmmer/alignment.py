import harp_pb2
import string

__format = string.Template(
'''
## $method $pdb$chain
# filt alignment (0.00% id)
scores_from_program: 0.0 0.0 0.0
$qstart $qalign
$tstart $talign
--
''')

COUNT_FROM_0 = 0
COUNT_FROM_1 = 1

def to_grishin(alignments, filename, counting_idx):
    '''Generates a Grishin-format alignment file from a set of alignments.
    Grishin format assumes counting begins at 0. If the input alignments
    start from any other index, specify it in `counting_idx`.'''
    assert counting_idx >= 0

    with open(filename, 'w') as file:
        for a in alignments:
            params = {
                'pdb'    : a.templ_pdb,
                'chain'  : a.templ_chain,
                'qstart' : a.query_start - counting_idx,
                'qalign' : a.query_align,
                'tstart' : a.templ_start - counting_idx,
                'talign' : a.templ_align,
                'method' : a.method,
                }

            file.write('%s\n' % __format.safe_substitute(params))
