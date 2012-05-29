CC = clang++
CFLAGS = -I/usr/local/include -I../../ -I../../common -fPIC
LDFLAGS = -L/usr/local/lib -L../../ -lboost_regex -lctemplate -lgflags -lglog -lharp -lprotobuf -lre2 -lzmq -g0 -O3

all: server

clean:
	rm -f *.o *.so *.pyc server

# binaries
server: parser.o server.o
	$(CC) $(LDFLAGS) $^ -o $@

# compile
%.o : %.cc
	$(CC) $(CFLAGS) -c $< -o $@
