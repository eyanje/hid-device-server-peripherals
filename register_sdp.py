#!/bin/env python3

from argparse import ArgumentParser
from itertools import chain
from pathlib import Path
from socket import AF_UNIX, SOCK_DGRAM, SOCK_SEQPACKET, socket
import sys
import time
import hid_server

parser = ArgumentParser(
        description='Advertise on the HID device server using an SDP record')
parser.add_argument('-r', '--hds-root',
        default='/run/hid-device-server')
parser.add_argument('sdp-record')

args = parser.parse_args()

hds_root = args.hds_root
sdp_path = args.__getattribute__('sdp-record')

server = hid_server.Server()

print('Conncting to command socket')
with server.command_socket() as command:
    print('Connected to command socket')

    with open(sdp_path, 'rb') as sdp_document:
        command.up(sdp_document.read())
        
        print('Advertising. Press ENTER to quit')
        input()

print('Done')
