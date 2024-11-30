#!/bin/env python3

from itertools import chain
from pathlib import Path
from socket import AF_UNIX, SOCK_SEQPACKET, socket
import sys
import time

base = Path(sys.argv[1])
print(f'Opening sockets at at {base}')

with open(base / 'ready') as ready_file:
    if ready_file.read() != '1':
        print('Not ready')
        exit(1)

print('Creating socket')
interrupt = socket(family=AF_UNIX, type=SOCK_SEQPACKET)
print('Conncting')
interrupt.connect(bytes(base / 'interrupt'))
print('Connected')

mouse_state = {
        'btn': [False, False, False],
        'rel': [0, 0]
        }

report = [
        0xA1, # DATA, input report (page 35)
        2, # mouse (page 42)
        0,
        0,
        0,
        ]

def clamp8(v):
    if v < -128:
        return -128
    if v > 127:
        return 127
    return v

frame = 0
while True:
    mouse_state['rel'][0] = -100 if frame % 2 == 0 else 100

    btn = mouse_state['btn']
    report[2] = btn[0] + (btn[1] << 1) + (btn[2] << 2);
    report[3] = clamp8(mouse_state['rel'][0]) & 0xFF
    report[4] = clamp8(mouse_state['rel'][1]) & 0xFF
    report_bytes = bytes(report)
    print(report_bytes)
    interrupt.send(report_bytes)

    frame += 1

    time.sleep(30e-3)

