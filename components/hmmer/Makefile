CC = clang++
CFLAGS = -isystem /opt/local/include -I../../ -I../../common -fPIC
LDFLAGS = -L/opt/local/lib -L../../ -lboost_regex -lctemplate -lgflags -lglog -lharp -lprotobuf -lre2 -lsnappy -lzmq -g0 -O3

all: server

clean:
	rm -f *.o *.so server

# binaries
server: parser.o server.o
	$(CC) $(LDFLAGS) $^ -o $@

# compile
%.o : %.cc
	$(CC) $(CFLAGS) -c $< -o $@
