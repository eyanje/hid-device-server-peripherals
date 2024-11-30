#!/bin/env python3

import asyncio
from evdev import ecodes, InputDevice, list_devices
from itertools import chain
from multiprocessing import Process
from pathlib import Path
from random import randint
from socket import AF_INET, AF_UNIX, SOCK_DGRAM, SOCK_SEQPACKET, socket
from threading import Thread
import struct
import sys
import time


port = int(sys.argv[1])


# Open connection sockets

base = Path(sys.argv[2])
print(f'Opening sockets at at {base}')

print('Creating socket')
interrupt = socket(family=AF_UNIX, type=SOCK_DGRAM)
print('Conncting')
interrupt.connect(bytes(base / 'interrupt'))
print('Connected')

def clamp8(v):
    v = round(v)
    if v < -128:
        return -128
    if v > 127:
        return 127
    return v

frame = 0

def pack_bits(bits):
    value = 0
    for offset, bit in enumerate(bits):
        value |= int(bit) << offset
    return value


async def handle_mouse():
    mouse_state = {
        'btn': [False, False, False],
        'rel': [0, 0, 0],
        'abs': [0, 0],
        }

    mouse_report = [
        0xA1, # DATA, input report (page 35)
        2, # mouse (page 42)
        0,
        0,
        0,
        0, # wheel
        ]

    input_sock = socket(AF_INET, SOCK_DGRAM)
    input_sock.bind(('0.0.0.0', port))

    position = [0, 0]

    while True:
        buf = input_sock.recv(1024)
        if len(buf) == 0:
            print('Empty buf received')
            break

        ev_type, ev_code, ev_value = struct.unpack('<HHi', buf)

        if ev_type == ecodes.EV_SYN:
            # Send a report
            btn = mouse_state['btn']
            mouse_report[2] = pack_bits(btn);
            mouse_report[3] = clamp8(mouse_state['rel'][0]) & 0xFF
            mouse_report[4] = clamp8(mouse_state['rel'][1]) & 0xFF
            mouse_report[5] = clamp8(mouse_state['rel'][2]) & 0xFF
            
            report_bytes = bytes(mouse_report)
            interrupt.send(report_bytes)

            # Reset rel
            mouse_state['rel'][0] = 0
            mouse_state['rel'][1] = 0
            mouse_state['rel'][2] = 0

        # Button presses
        if ev_type == ecodes.EV_KEY:
            # Ignore duplicates
            if ev_value == 2:
                continue
            if ev_code == ecodes.BTN_TOUCH:
                mouse_state['btn'][0] = ev_value

                # On release, clear absolute values
                if ev_value == 0:
                    mouse_state['abs'][0] = None
                    mouse_state['abs'][1] = None

            # Mouse buttons
            if ev_code in [ecodes.BTN_LEFT, ecodes.BTN_0]:
                mouse_state['btn'][0] = ev_value
            if ev_code in [ecodes.BTN_RIGHT, ecodes.BTN_1]:
                mouse_state['btn'][1] = ev_value
            if ev_code == ecodes.BTN_MIDDLE:
                mouse_state['btn'][2] = ev_value

        # Touch movements
        mode = 'horizontal'
        mode = 'remote'
        l_sensitivity = 2e-2
        r_sensitivity = 1e0
        if ev_type == ecodes.EV_REL:
            if mode == 'horizontal':
                if ev_code == ecodes.REL_X:
                    mouse_state['rel'][0] -= l_sensitivity * ev_value
                if ev_code == ecodes.REL_Y:
                    mouse_state['rel'][1] += l_sensitivity * ev_value
            elif mode == 'vertical':
                if ev_code == ecodes.REL_X:
                    mouse_state['rel'][1] -= l_sensitivity * ev_value
                if ev_code == ecodes.REL_Y:
                    mouse_state['rel'][0] -= l_sensitivity * ev_value
            elif mode == 'remote':
                if ev_code == ecodes.REL_X:
                    mouse_state['rel'][1] -= l_sensitivity * ev_value
                if ev_code == ecodes.REL_Z:
                    mouse_state['rel'][0] -= l_sensitivity * ev_value

            if ev_code == ecodes.REL_RX:
                mouse_state['rel'][0] += r_sensitivity * ev_value
                position[0] += ev_value
            if ev_code == ecodes.REL_RY:
                mouse_state['rel'][1] += r_sensitivity * ev_value
                position[1] += ev_value
    

async def main():
    async with asyncio.TaskGroup() as tg:
        mouse_task = tg.create_task(handle_mouse())

    print(key_task.result(), mouse_task.result())

asyncio.run(main())
