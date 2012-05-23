CC = clang++
CFLAGS = -isystem /opt/local/include -I../../ -I../../common -fPIC
LDFLAGS = -L/opt/local/lib -lboost_regex -lctemplate -lgflags -lglog -lprotobuf -lsnappy -lzmq -g0 -O3

all: server

clean:
	rm -f *.o *.so server

# binaries
server: parser.o util.o server.o
	$(CC) $(LDFLAGS) $^ harp.so -o $@

# compile
%.o : %.cc
	$(CC) $(CFLAGS) -c $< -o $@
