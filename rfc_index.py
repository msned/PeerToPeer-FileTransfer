#!/usr/bin/env python3

"""
This keeps track of RFC indexes in regard to each peer, within a linked list structure.

@author: anfisher
"""


class RFCIndex:
    """
    The linked list representation for the RFC Index
    """
    def __init__(self):
        self.head = None

    def append(self, data):
        if not self.head:
            self.head = Node(data=data)
            return
        else:
            current = self.head
            while current.next:
                current = current.next
            current.next = Node(data=data)

    def remove(self, node):
        current = self.head
        prev = None
        while current and current != node:
            prev = current
            current = current.next
        # print("prev ", prev.data.data.rfc_num)
        print("ttl timeout: removing rfc ", current.data.data.rfc_num)
        if not prev:
            self.head = current.next
        elif current:
            prev.next = current.next
            current.next = None

    def get(self, rfc_num):
        current = self.head
        while current and current.data.data.rfc_num != rfc_num:
            current = current.next
        return current

    def get_all(self):
        data_list = []
        current = self.head
        while current:
            data_list.append(current.data)
            current = current.next

        return data_list


class Node:
    """
    Linked list element.  Data will be an instance of RFC_data
    """
    def __init__(self, data=None):
        self.data = data
        self.next = None


class RFCData:
    """
    Data that comprises an element in the RFC Index table
    """
    def __init__(self, rfc_num, rfc_title, hostname, port, ttl):
        self.rfc_num = rfc_num
        self.rfc_title = rfc_title
        self.hostname = hostname
        self.port = port
        self.ttl = ttl
