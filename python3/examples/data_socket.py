from popoto.popoto import popoto
from socket import socket, timeout as SocketTimeout, AF_INET, SOCK_STREAM

POPOTO_IP = 'localhost'
PORT_NUM = 17000

if __name__ == '__main__':
    modem = popoto(POPOTO_IP, PORT_NUM)                             # Construct our popoto object. The first argument is the IP address and the second is the base port number.
                                                                        # Note that the modem will use ports from basePort to basePort+5. See popoto.py for details.
    data_socket = socket(AF_INET, SOCK_STREAM)                      # Construct our socket. Use the "inet" address family and "stream" socket kind.
    data_socket.connect(
            (                                                       # A socket is constructed with a tuple, consisting of the IP address and port to connect to
                modem.ip,                                           # This is the IP address of the modem as defined when constructing it on line 8
                modem.cmdport                                       # This will return the command port on the modem in relation to the base port defined in the constructor on line 8
            )
        )
    data_socket.settimeout(3)                                       # Set a timeout of 3 seconds on our socket to prevent indefinite hanging.

    print("Sending \"TransmitJSON\" command...")
    json_message = '{"Hello":"World"}'
    modem.transmitJSON(json_message)                                # Send the JSON through the modem directly.
    output_str = ""

    while True:                                                     # Loop to receive data from the modem's command socket.
        try:
            byte = data_socket.recv(1)                              # Attempt to receive one byte at a time and print it without a newline.
            if byte == b'\r':                                       # Carriage returns indicate new lines.
                output_str += '\n'
            output_str += byte.decode('utf8')
        except SocketTimeout:                                       # When the socket times out, print a new line and break.
            print()
            data_socket.close()                                     # Close the data socket.
            modem.tearDownPopoto()                                  # Tear down the modem cleanly.
            break
    
    print()
    print("Final output: \n" + output_str)                          # Prints the output as received. Note that this might be redundant, as command outputs are usually automatically printed to stdout by the popoto.