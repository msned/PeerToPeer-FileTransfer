#!/usr/bin/env python3

"""
This handles the server functions of a peer in our P2P-DI system.

@author: anfisher, msnedec
"""
import socket
from threading import Thread, BoundedSemaphore
import glob
import os
import struct
from rfc_index import RFCIndex, Node, RFCData
import time


# Global variable for the RFC index of the peer (this can be moved to a __main__
#  method when we combine the client and server peer code)
rfcIndex = RFCIndex()

# Dictionary for port numbers for each hostname
portLookup = {}

# host address
ip = socket.gethostbyname(socket.gethostname())

# reserve a port number
port = 50001

# Store of local RFC
localRFC = set()

# Variable that tells the server to keep running
running = True

# Semaphore for accessing index
indexLock = BoundedSemaphore(1)


# Populates RFCs from current directory
def populate_rfc_index(input_dir):
    rfc_files = glob.glob(input_dir + "/*.txt")
    rfc_files.sort()
    for rfc_file in rfc_files:
        with open(rfc_file, "r") as rfc:
            rfc_num = os.path.basename(rfc_file)[3:7]
            hostname = ip

            # to get the title, read lines until one starts with "Abstract"
            # (the title is above this)
            lines = rfc.readlines()
            for i, line in enumerate(lines):
                if line.startswith("Abstract"):
                    # The title might be more than one line of text, so join
                    # three lines above 'Abstract' and strip any extra whitespace
                    rfc_title = " ".join([token.strip() for token in lines[i-3:i]]).strip()
                    break
            rfc = RFCData(rfc_num, rfc_title, hostname, port, 7200)
            rfc_node = Node(rfc)

            # Add to index after acquiring semaphore
            indexLock.acquire()
            rfcIndex.append(rfc_node)
            indexLock.release()

            # Add record to local set
            localRFC.add(rfc_num)


# Retrieve RFC data for missing RFCs
def findMissingRFCs():
    RFCMissingList = []
    # Acquire semaphore before scanning index
    indexLock.acquire()

    RFCList = rfcIndex.get_all()

    for RFC in RFCList:
        if RFC.data.rfc_num not in localRFC:
            RFCAttributes = [RFC.data.hostname, RFC.data.port, RFC.data.rfc_num]
            RFCMissingList.append(RFCAttributes)
    # Release access to index
    indexLock.release()

    return RFCMissingList


# Successfully added RFC to local
def addLocalRFC(rfcnum):
    localRFC.add(rfcnum)


# Sets the value of global running variable
def setRunning(run):
    global running
    indexLock.acquire()
    running = run
    indexLock.release()


# Returns set of local RFC files
def returnLocalSet():
    return localRFC


def get_rfc_query_response():
    # build and return encoded string containing the RFC Response and data messages

    # create list of RFCQueryData strings
    query_data_strings = []

    indexLock.acquire()
    data_list = rfcIndex.get_all()
    indexLock.release()

    for i in data_list:
        rfc_query_data = "{} {} {} {}\r\n".format(i.data.rfc_num, i.data.rfc_title, i.data.hostname, i.data.port)
        query_data_strings.append(rfc_query_data)

    # create single string of all RFC Index data
    query_data = "".join(query_data_strings)

    # get num bytes for data when building the response header
    num_bytes = len(query_data.encode('utf-8'))

    # build the response header
    response = ("RFCQueryResponse {} P2P-DI\r\n"
                "host: {}\r\n"
                "size: {}\r\n"
                "IndexLength: {} \r\n\r\n").format("200", ip,
                                                   num_bytes, len(data_list))

    # return response then query data
    return (response + query_data).encode('utf-8')


# Return response and rfc contents
def get_rfc_file_response(rfc_num, input_dir):
    # store file contents in variable
    with open("{}/rfc{}.txt".format(input_dir, rfc_num), "r") as rfc_file:
        rfc_contents = rfc_file.read()

        num_bytes = len(rfc_contents.encode('utf-8'))

        response = "GetRFC 200 P2P-DI\r\nsize: {}\r\n\r\n".format(num_bytes)

        # return response then rfc_contents
        return (response + rfc_contents).encode('utf-8')


# Send a specified message
def send_message(sock, message):
    message = struct.pack('>I', len(message)) + message
    sock.sendall(message)


# Return RFC index
def get_rfc_index():
    return rfcIndex


# Return port lookup
def getPortLookup():
    return portLookup


# Handle request from peer client
def handle_peer_request(client, address, input_dir):
    print("\nReceived Connection From Peer")

    # loop until we receive a message
    while True:
        # store and decode the message
        message = client.recv(1024).decode('utf-8')
        if not message:
            break

        print("\nServer Received Message:\n" + message + '\n')

        # the peer can perform an RFCQuery or GetRFC
        if message.startswith('RFCQuery'):
            # RFCQuery- the peer requests the RFCIndex

            send_message(client, get_rfc_query_response())

        elif message.startswith('GetRFC'):
            # GetRFC- the peer requests to download a specific RFC

            # get the rfc number
            rfc_num = message.split('\r\n')[2].split(':')[1].strip()

            send_message(client, get_rfc_file_response(rfc_num, input_dir))


# Periodically update TTL value
def ttl_handler():
    global running
    while running is True:
        # every x number of seconds, we iterate through the rfc list and decrement
        # by x if the rfc entry is not the local one.

        current = rfcIndex.head
        while current:
            # if the rfc is hosted locally, we don't decrement ttl
            if not current.data.data.hostname == ip:
                # decrement the ttl field by x. If doing so results in a ttl <= 0,
                # remove the node from the index
                current.data.data.ttl -= 60
                if current.data.data.ttl <= 0:
                    rfcIndex.remove(current)

            current = current.next
        
        for i in range(60):
            time.sleep(1)
            if running is False:
                break


# The starting method for the client server module
def startServer(input_dir, peer_server_port):
    """
    Listens to the peer-specific port. When a connection from a remote peer
    is received, spawn a new thread that handles the downloading for this
    remote peer. Then return to listening for other connection requests.
    Once the downloading completes, the new thread terminates.
    """
    global port

    print("Peer Server Started on Port: ", str(peer_server_port))
    port = int(peer_server_port)

    # create RFC index from files in input directory
    populate_rfc_index(input_dir)

    # create a tcp socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # establish connection
    s.bind((ip, port))

    # start listening for connections
    s.listen(5)

    # start a thread that handles ttl
    ttl_thread = Thread(target=ttl_handler)
    ttl_thread.start()

    # loop while listening
    while running is True:
        # connect with a client
        client, address = s.accept()

        # spawn a new thread that handles downloading from this peer
        thread = Thread(target=handle_peer_request, args=(client, address, input_dir))
        thread.start()
        thread.join()
    ttl_thread.join()
    s.close()
