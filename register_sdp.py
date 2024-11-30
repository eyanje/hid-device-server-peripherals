#!/bin/env python3

from itertools import chain
from pathlib import Path
from socket import AF_UNIX, SOCK_DGRAM, SOCK_SEQPACKET, socket
import sys
import time

command_path = Path(sys.argv[1])
sdp_path = Path(sys.argv[2])

print('Creating command socket')
bufsize = 1024
with socket(family=AF_UNIX, type=SOCK_SEQPACKET) as command:
    print('Conncting to command socket')
    command.connect(bytes(command_path))
    print('Connected to command socket')

    with open(sdp_path, 'rb') as sdp_document:
        command.send(bytes(chain(
            [1],
            sdp_document.read()
            )))
        reply = command.recv(bufsize)
        print(f'reply: {reply}')
    
    input()

