#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This handles the client functions of a peer in our P2P-DI system.

@author: msnedec, anfisher
"""

import socket
import argparse
import struct
from peer_server import startServer
import peer_server
import sys
from threading import Thread
from rfc_index import RFCIndex, Node, RFCData
import time

'''
On data transfers need to add an acknowledgment packet sent to let the server
know to start sending

When leaving, stay active to finish all current transfers and let all threads join
without making any new ones
'''


# Cookie for communications with RS server, default is 0 and is assigned a higher value
cookie = 0

# Boolean value for checking when connected
connected = False

# Server Ip, changed to wherever the server is running
server_host = "127.0.0.1"

# Server port number, well known
server_port = 65243

# Port of the client
hostaddress = socket.gethostbyname(socket.gethostname())

# Port of the client
hostport = "50000"

# list of peers (dictionary won't work for multiple peers on same IP)
# consists of elements of [peer ip, peer port]
peerList = []

# Global variable for knowing whether the program should be running
running = True


# Creates the message to register the client
def registerMessage():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((server_host, server_port))
    message = "Register P2P-DI\r\nhost: " + hostaddress + "\r\ncookie: "
    message += str(cookie) + "\r\nport: " + str(hostport) + "\r\n\r\n"
    s.send(message.encode('utf-8'))

    regResponse = s.recv(1024).decode('utf-8')
    print('\nRegister Response Received: ' + regResponse)
    registerResponseHandler(regResponse)
    s.close


# Handles the server response from registering
def registerResponseHandler(regResponse):
    global cookie
    global connected

    returned = regResponse.split()

    if returned[1] == '200':
        connected = True
        returnedCookie = int(returned[4])
        if returnedCookie != cookie:
            cookie = returnedCookie


# Client to server message for Leave, KeepAlive, PQuery
def serverMessages(messageType):
    global running
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((server_host, server_port))

    # Send the request with headers
    message = messageType + " P2P-DI\r\nhost: " + hostaddress + "\r\ncookie: "
    message += str(cookie) + "\r\n\r\n"
    s.send(message.encode('utf-8'))

    if messageType == "PQuery":
        PQueryResponseHandler(s)
    if messageType == "Leave":
        running = False
    s.close()


# handles the response from the PQuery
def PQueryResponseHandler(s):
    global peerList

    # Get response to the query with the size of the data
    returned = s.recv(1024).decode('utf-8')
    print('\nPQuery Response Received:\n' + returned)
    if returned.split()[1] == '400':
        print("No Active Peers")
        peerList = []
        return

    full_msg = returned.split("\r\n\r\n")

    headers = full_msg[0].split()
    peers = full_msg[1].split()

    byte_size = int(headers[4])
    length = int(headers[6])

    newList = []
    for i in range(length):
        # if the host address of the peer is local, the peer server port must be
        # from another peer
        if (peers[i*2] == hostaddress) and (int(peers[(i*2)+1]) != int(hostport)):
            list_element = [peers[i*2], peers[(i*2)+1]]
            newList.append(list_element)
        # if the host address is not local, we add the peer to the dict
        if peers[i*2] != hostaddress:
            list_element = [peers[i*2], peers[(i*2)+1]]
            newList.append(list_element)

    peerList = newList


# Queries other peers for their list of RFCs
def RFCQueryMessage(peerName, peerPort):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((peerName, int(peerPort)))

    # Send main header with request
    message = 'RFCQuery P2P-DI\r\nhost: ' + hostaddress
    s.send(message.encode('utf-8'))

    # handle the server response
    RFCQueryResponse(s)

    s.close()


def receive_all(sock, length):
    data = b''
    while len(data) < length:
        packet = sock.recv(length - len(data))
        if not packet:
            return None
        data += packet
    return data


def receive_long_message(sock):
    raw_msglen = receive_all(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    return receive_all(sock, msglen)


# Handles server response to RFC query
def RFCQueryResponse(s):

    response = receive_long_message(s).decode('utf-8')

    headers = response.split("\r\n\r\n")[0].split()
    RFCIndexData = response.split("\r\n\r\n")[1].split("\r\n")

    print("RFC Query Response Received: \n" + response)
    if headers[1] == '200':
        # How many RFCs are being sent
        length = int(headers[8])
        for i in range(length):
            # get the host's current rfc index
            index = peer_server.get_rfc_index()

            # Split each line into values
            line = RFCIndexData[i].split()

            # try to find an existing Record of the RFC number
            existingRecord = index.get(line[0])

            # line[0] is the RFC number of one element of RFCIndexData
            # line[1-??] is the title
            # line[-1] is the port number
            # line[-2] is the address

            # Checks that the record doesn't already exist in index and then adds it
            if existingRecord is None or existingRecord.data.data.hostname != line[-2] or existingRecord.data.data.port != line[-1]:
                rfc = RFCData(line[0], " ".join(line[1:-2]), line[-2], line[-1], 7200)
                rfc_node = Node(rfc)
                index.append(rfc_node)
    else:
        print("No RFC Index Available")


# Asks for a specific document from peer
def GetRFCMessage(peerName, peerPort, rfcnum):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((peerName, int(peerPort)))

    # Send main header with request
    message = 'GetRFC P2P-DI\r\nhost: ' + hostaddress + "\r\nRFCIndex: " + rfcnum
    s.send(message.encode('utf-8'))

    # handle the server response
    status = GetRFCHandler(s, rfcnum)

    s.close()
    return status


# Handles receiving RFC file
def GetRFCHandler(s, rfcnum):
    # Receive response header

    response = receive_long_message(s).decode('utf-8')

    headerData = response.split("\r\n\r\n")[0]
    print('\nDownloading RFC Response\n' + headerData)
    headers = headerData.split()
    RFC = response.split("\r\n\r\n")[1]

    if headers[1] == '200':
        with open("{}/rfc{}.txt".format(sys.argv[1], rfcnum), "w") as newRFC:
            newRFC.write(RFC)
            return True
    else:
        print("RFC File not found")
        return False


# Separate thread for the client's server to run on
def serverStart(input_dir, peer_server_port):
    startServer(input_dir, peer_server_port)


# Parses command line arguments
def construct_argparser():
    """
    Uses argparse module to retrieve command line arguments. Users should enter
    the directory of their local RFC files
    """
    parser = argparse.ArgumentParser(description="Peer")
    parser.add_argument("input_dir", help="directory of local RFC files")
    parser.add_argument("reg_server", help="hostname of the registration server")
    parser.add_argument("peer_server_port", type=int, help="desired port of peer_server")
    return parser


# Routinely sends Keep alive packet so server knows that client is active
def keepClientAlive():
    global running
    while running is True:
        # Send packet every seconds so that the server knows the client is active
        serverMessages("KeepAlive")

        for i in range(300):
            time.sleep(1)
            if running is False:
                break
        

# Queries peers for updated rfc index
def updateRFC():
    for peer in peerList:
        RFCQueryMessage(peer[0], peer[1])


# Downloads rfcs from peers
def downloadRFC():
    missingRFCs = peer_server.findMissingRFCs()
    print("Download all rfcs(All) or specified number (#)")
    s = input('=>')
    if s == 'All':
        limit = len(missingRFCs)
    else:
        limit = int(s)

    for i in range(limit):
        status = GetRFCMessage(missingRFCs[i][0], missingRFCs[i][1], missingRFCs[i][2])
        if status is True:
            peer_server.addLocalRFC(missingRFCs[i][2])
    

# Connects to all current server threads to close them
def closeServerConnections():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((hostaddress, int(hostport)))
        s.send("ShutDown".encode('utf-8'))
        s.close()
    except socket.error:
        return
    closeServerConnections()


if __name__ == "__main__":
    # creates list of command line arguments
    args = construct_argparser().parse_args()

    # Start separate thread to run server module
    serverThread = Thread(target=serverStart, args=(args.input_dir,args.peer_server_port))
    serverThread.start()

    # Assign registration server to server hostname
    server_host = args.reg_server
    hostport = args.peer_server_port
    print("Registration Server hostname is '" + str(server_host) + "'")
    print("The local peer hostname is '" + hostaddress + "'")
    print("The peer port number is '" + str(hostport) + "'")

    # Try and connect with the RS server to get cookie
    while not connected:
        registerMessage()

    # Start thread to send message to server every 5 minutes
    registerThread = Thread(target=keepClientAlive, args=())
    registerThread.start()

    while running is True:
        print("(Q) query for RFCs\n(G) get missing RFCs\n(P) Check active peers\n(L) Leave the network\n")
        s = input('=>')
        if s == 'Q':
            serverMessages("PQuery")
            updateRFC()
        elif s == 'G':
            downloadRFC()
        elif s == 'P':
            serverMessages("PQuery")
        elif s == 'L':
            serverMessages("Leave")
            peer_server.setRunning(False)
        else:
            print("Invalid input")
    registerThread.join()
    
    closeServerConnections()
    
    serverThread.join()
