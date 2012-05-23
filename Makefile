CC = clang++
CFLAGS = -I/opt/local/include -Icommon -fPIC
LDFLAGS = -L/opt/local/lib -lgflags -lglog -lprotobuf -lsnappy -lzmq -g0 -O3

# See GNU Make, section "Chains of Implicit Rules"
# ftp://ftp.gnu.org/pub/pub/old-gnu/Manuals/make-3.79.1/html_chapter/make_10.html#SEC97
.SECONDARY: harp.pb.cc

all: broker client sink source splitter worker

clean:
	rm -f *.o *.so *.pb.cc *.pb.h broker client sink source splitter worker

# binaries
broker: broker.o
	$(CC) $(LDFLAGS) $^ -o $@

client: harp.so client.o
	$(CC) $(LDFLAGS) $^ -o $@

sink: harp.so sink.o
	$(CC) $(LDFLAGS) $^ -o $@

source: source.o
	$(CC) $(LDFLAGS) $^ -o $@

splitter: splitter.o
	$(CC) $(LDFLAGS) $^ -o $@

worker: worker.o
	$(CC) $(LDFLAGS) $^ -o $@

# libraries
harp.so : harp.pb.o
	$(CC) $(LDFLAGS) -fPIC -shared $^ -o $@

# compile
%.o : %.cc
	$(CC) $(CFLAGS) -c $< -o $@

# genproto
%.pb.cc %.pb.h : %.proto
	protoc --cpp_out=. $<
