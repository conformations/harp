CC = clang++
CFLAGS = -I/opt/local/include -I../../ -I../../common -fPIC
LDFLAGS = -L/opt/local/lib -lctemplate -lgflags -lglog -lprotobuf -lsnappy -lzmq -g0 -O3

# See GNU Make, section "Chains of Implicit Rules"
# ftp://ftp.gnu.org/pub/pub/old-gnu/Manuals/make-3.79.1/html_chapter/make_10.html#SEC97
.SECONDARY: harp.pb.cc

all: server

clean:
	rm -f *.o *.so *.pb.cc *.pb.h server

# binaries
server: parser.o server.o
	$(CC) $(LDFLAGS) $^ ../../*.so -o $@

# compile
%.o : %.cc
	$(CC) $(CFLAGS) -c $< -o $@
