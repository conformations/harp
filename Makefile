CC = clang++
CFLAGS = -isystem /opt/local/include -Icommon -fPIC
LDFLAGS = -L/opt/local/lib -lboost_regex -lgflags -lglog -lprotobuf -lzmq -g0 -O3

# See GNU Make, section "Chains of Implicit Rules"
# ftp://ftp.gnu.org/pub/pub/old-gnu/Manuals/make-3.79.1/html_chapter/make_10.html#SEC97
.SECONDARY: harp.pb.cc

all: broker client sink source splitter worker

clean:
	rm -f *.o *.so *.pb.cc *.pb.h *_pb2.py broker client sink source splitter worker

# binaries
broker: broker.o
	$(CC) $(LDFLAGS) $^ -o $@

client: libharp.so client.o
	$(CC) $(LDFLAGS) $^ -o $@

sink: libharp.so sink.o
	$(CC) $(LDFLAGS) $^ -o $@

source: source.o
	$(CC) $(LDFLAGS) $^ -o $@

splitter: splitter.o
	$(CC) $(LDFLAGS) $^ -o $@

worker: worker.o
	$(CC) $(LDFLAGS) $^ -o $@

# libraries
libharp.a : harp.pb.o str_util.o
	$(CC) $(LDFLAGS) -fPIC -static $^ -o $@

libharp.so : harp.pb.o str_util.o
	$(CC) $(LDFLAGS) -fPIC -shared $^ -o $@

# compile
%.o : %.cc
	$(CC) $(CFLAGS) -c $< -o $@

# genproto
%.pb.cc %.pb.h : %.proto
	protoc --cpp_out=. --python_out=. $<

