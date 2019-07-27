#!/usr/bin/env python3

"""
This peer_list_control keeps track of peers, and relevant information in regard to each peer, within a
linked list structure.

@author: anfeisal
"""

import time
import threading

# Declare initial TTL value (in seconds)
INITIAL_TTL = 7200
# Declare base cookie value --> increments for each cookie, so first peer will have a cookie with value 1
COOKIE_COUNTER = 0

# Create lock mechanism for multi-threading
lock = threading.Lock()


# Generate a new cookie value, incremented for every registered peer
def create_cookie():
    global COOKIE_COUNTER

    # Increment if lock is first acquired, then release  lock
    with lock:
        COOKIE_COUNTER = COOKIE_COUNTER + 1

    return COOKIE_COUNTER


class PeerNode:
    """
    The PeerNode class stores information for peers within a PeerList, maintained by the Registration server.
    It stores the 7 variables for a peer: its hostname, cookie, TTL, port number, the number of times it has
    registered, and the timestamp (date and time) that it last registered. The node also keeps track of the next
    node which will follow it in the PeerList, which is implemented as a linked list.
    """

    # Initializer / Instance Attributes
    def __init__(self, host_name, cookie, is_active, ttl, port_num, num_times_active, last_registered_ts):
        self.host_name = host_name
        self.cookie = cookie
        self.is_active = is_active
        self.ttl = ttl
        self.port_num = port_num
        self.num_times_active = num_times_active
        self.last_registered_ts = last_registered_ts
        self.registration_record = []
        self.next_node = None

    # Increment the number of times a peer has been active/registered
    def inc_num_times_active(self):
        self.registration_record.append(time.time())
        self.num_times_active = len(self.registration_record)

    # Initializes the first time a peer is active
    def set_first_num_active(self):
        self.inc_num_times_active()

    # Remove number of times a peer has been active if it's been past 30 days (2592000)
    def update_num_times_active(self):
        if self.num_times_active is 0:
            return

        time_lapse = time.time() - self.registration_record[0]
        while time_lapse > 2592000:
            self.registration_record.pop(0)
            self.num_times_active = len(self.registration_record)

            if self.num_times_active is 0:
                return

            time_lapse = time.time() - self.registration_record[0]

    # Check num times active every 10 days (864000 seconds)
    def init_num_times_active_check(self):
        self.update_num_times_active()
        threading.Timer(864000.0, self.init_num_times_active_check).start()

    # Return the cookie value for the peer
    def get_cookie(self):
        return self.cookie

    # Return active value for peer (true or false)
    def get_active(self):
        return self.is_active

    # Return hostname for peer
    def get_host_name(self):
        return self.host_name

    # Return port number for peer
    def get_port_num(self):
        return self.port_num

    # Set next PeerNode in linked list
    def set_next(self, next_node):
        self.next_node = next_node

    # Return next node in linked list
    def get_next(self):
        return self.next_node

    # Set active value for peer node
    def set_active(self, status):
        self.is_active = status

    # Reset TTL for peer to original value (7200)
    def reset_ttl(self):
        self.ttl = INITIAL_TTL

    # Update timestamp that peer was last registered
    def update_time(self):
        self.last_registered_ts = time.ctime()

    # Decrement TTL value by 10 seconds
    def dec_ttl_by_ten(self):
        self.ttl = self.ttl - 1

    # Check if TTL amount has fully decremented
    def check_ttl(self):
        if self.ttl <= 0:
            self.set_active(False)

    # Initialize periodic countdown for TTL (every 10 seconds)
    def init_ttl(self):
        self.check_ttl()
        self.dec_ttl_by_ten()
        threading.Timer(10.0, self.init_ttl).start()


class PeerList:
    """
    The PeerList class maintains a linked list format for a collection of PeerNodes. It allows you to find a
    PeerNode by its cookie value, and add new PeerNodes to the list if it is their first time being registered.
    This class also allows you to determine the size/length of the current PeerList.
    """

    # Initializer / Instance Attributes
    def __init__(self):
        self.head = None

    # Find PeerNode in list based on specified cookie number
    def find(self, p_cookie):
        current = self.head
        while current is not None:
            if current.cookie == p_cookie:
                break
            current = current.get_next()
        return current

    # Add new PeerNode to PeerList with specified hostname and port number
    def add(self, host_name, port_num):
        cookie = create_cookie()
        timestamp = time.ctime()

        peer_node = PeerNode(host_name, cookie, True, INITIAL_TTL, port_num, 0, timestamp)
        peer_node.set_first_num_active()
        peer_node.init_ttl()
        peer_node.init_num_times_active_check()

        peer_node.set_next(self.head)
        self.head = peer_node
        return cookie

    # Return length of PeerList, or the amount of peers within a PeerList
    def size(self):
        current = self.head
        count = 0
        while current:
            count = count + 1
            current = current.get_next()
        return count
