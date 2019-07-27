#!/usr/bin/env python3

"""
The reg-server (Registration Server) communicates with peers and keeps track of registered peers
through a PeerList.

@author: anfeisal, msnedec
"""

import socket
from peer_list_control import PeerNode, PeerList
import sys
from threading import Thread, BoundedSemaphore


# List of peers in system
peerlist = PeerList()

# Semaphore for accessing peer list
peerSem = BoundedSemaphore(1)


# For each connection, determines what request was made
def client_request_handler(client, address):
    # Receive variable size message with headers
    recv_message = client.recv(1024).decode('utf-8')

    typeOfRequest = recv_message.split()[0]

    if typeOfRequest == "Register":
        print("Received Registering Message:\n" + recv_message)
        cookie = register(recv_message)

        # Create message to send back response with cookie value
        message = "RegisterResponse 200 P2P-DI\r\nCookie: " + cookie + "\r\n\r\n"
        client.send(message.encode('utf-8'))
    elif typeOfRequest == "Leave":
        print("Received Leaving Message:\n" + recv_message)
        leave(recv_message)
    elif typeOfRequest == "KeepAlive":
        print("Received Keep Alive Message:\n" + recv_message)
        keep_alive(recv_message)
    elif typeOfRequest == "PQuery":
        active_peers, length = pquery()
        print("Received Peer Query:\n" + recv_message)

        # Add additional branch where if there are no peers besides itself
        # then send 400 error
        if length == 1:
            message = "PQueryResponse 400 P2P-DI\r\n"
        else:
            # Send response with byte size and length of message containing
            #  information on active peers
            message = "PQueryResponse 200 P2P-DI\r\n"
            message += "Size: " + str(sys.getsizeof(active_peers)) + "\r\n"
            message += "Length: " + str(length) + "\r\n\r\n"
            message += active_peers
        client.send(message.encode('utf-8'))


# Registers new peers and updates returning ones to active
def register(register_message):
    global peerlist

    # Grabs peer values from request headers
    headers = register_message.split()
    peer_host = headers[3]
    old_cookie = headers[5]
    peer_port = headers[7]

    # Finds if peer already registered and update it, if not it adds it
    peerSem.acquire()

    peer_entry = peerlist.find(int(old_cookie))
    if peer_entry is None:
        # Peer is not in list, add it to list
        new_cookie = str(peerlist.add(peer_host, peer_port))
    else:
        # Peer has previously registered, update its instance in list
        #  by making it active, incrementing the number of times it's
        #  been active, reset the TTL value to 7200 (seconds), and
        #  update its last registered timestamp
        new_cookie = old_cookie
        peer_entry.set_active(True)
        peer_entry.inc_num_times_active()
        peer_entry.reset_ttl()
        peer_entry.update_time()

    peerSem.release()

    # Return cookie for the entry
    return new_cookie


# The server marks the peer that is leaving as inactive
def leave(recv_message):
    global peerlist
    headers = recv_message.split()

    # Cookie of leaving peer
    cookie = headers[5]

    peerSem.acquire()
    peer_entry = peerlist.find(int(cookie))
    peer_entry.set_active(False)
    peerSem.release()


# Resets the TTL field for a peer so server knows its active
def keep_alive(recv_message):
    global peerlist
    headers = recv_message.split()

    # Cookie of peer
    cookie = headers[5]

    peerSem.acquire()
    peer_entry = peerlist.find(int(cookie))
    peer_entry.reset_ttl()
    peerSem.release()


# Returns a list of peers to a client
def pquery():
    global peerlist
    active_peers = ""
    peerSem.acquire()

    # Find active peers in list
    current = peerlist.head
    count = 0
    while current is not None:
        # If peer is active, add it to string representation
        if current.get_active() is True:
            active_peers += current.get_host_name() + " " + str(current.get_port_num()) + "\r\n"
            count = count + 1
        
        current = current.get_next()
    peerSem.release()
    active_peers += "\r\n"
    return active_peers, count


if __name__ == "__main__":
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = socket.gethostbyname(socket.gethostname())   # Get machine name
    port = 65243                  # Reserve a port for your service.
    print("Registration Server running on host '" + str(host) + "' at port number '" + str(port) + "'")
    s.bind((host, port))          # Bind to the port
    s.listen()                    # Now wait for client connection.

    while True:
        client, addr = s.accept()  # Establish connection with client.
        print('Got connection from', addr)

        # Allocate thread to communicate with client (peer)
        thread = Thread(target=client_request_handler, args=(client, addr))
        thread.start()
        thread.join()
    s.close
