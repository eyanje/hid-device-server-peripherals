#!/bin/env python3

from itertools import chain
from pathlib import Path
from random import randint
from socket import AF_UNIX, SOCK_SEQPACKET, socket
import sys
import time

from ascii_to_hid import *

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

key_report = [
        0xA1, # DATA, input report (page 35)
        1, # keyboard (page 42)
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        ]

mouse_report = [
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

def pack_bits(bits):
    value = 0
    for offset,value in enumerate(bits):
        value |= value << offset
    return value

while True:
    # key_state['key'][HID_KEY_A] = bool(frame % 2)

    mouse_state['rel'][0] = -100 if frame % 2 == 0 else 100

    # Set the first pressed key
    key_report[4] = HID_KEY_A if frame % 2 == 0 else HID_KEY_NONE

    btn = mouse_state['btn']
    mouse_report[2] = pack_bits(btn);
    mouse_report[3] = clamp8(mouse_state['rel'][0]) & 0xFF
    mouse_report[4] = clamp8(mouse_state['rel'][1]) & 0xFF

    report_bytes = bytes(key_report)
    print(report_bytes, flush=True)
    interrupt.send(report_bytes)

    report_bytes = bytes(mouse_report)
    #print(report_bytes, flush=True)
    interrupt.send(report_bytes)

    frame += 1

    time.sleep(100e-3)

