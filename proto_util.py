import google.protobuf as pb

def proto_recv(socket, message):
    '''Reads a text-format protocol buffer from `socket` into `message`'''
    pb.text_format.Merge(socket.recv(), message)

def proto_send(socket, message):
    '''Sends a text-format protocol buffer to `socket`'''
    socket.send(str(message))
