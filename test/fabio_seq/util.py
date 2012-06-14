# Collection of utility routines
import fnmatch, os, shutil

def locate(pattern, root = os.curdir):
    for path, dirs, files in os.walk(os.path.abspath(root)):
        for filename in fnmatch.filter(files, pattern):
            yield os.path.join(path, filename)


def frange(start, stop, step):
    '''Identical to built-in range function, but with floating point step'''
    while start <= stop:
        yield start
        start += step
                        

def read_fasta(filename):
    '''Returns the sequence contained in a FASTA format file'''
    seq = ''
    with open(filename) as file:
        file.readline()

        for line in file:
            line = line.strip()
            seq += line

    return seq


def attempt_rm(filename):
    '''Attempts to remove the given file, returning true if successful, false otherwise'''
    try:
        os.remove(filename)
        return True
    except:
        return False


def attempt_rmdir(path):
    shutil.rmtree(path, ignore_errors = True)


def attempt_mv(src, dst):
    '''Attempts to move src to destination, returning true if successful, false otherwise'''
    try:
        shutil.move(src, dst)
        return True
    except:
        return False

def touch(fname, times = None):
    '''*nix touch command'''
    with file(fname, 'a'):
        os.utime(fname, times)
