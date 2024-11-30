#!/bin/env python3

import asyncio
from evdev import ecodes, InputDevice, list_devices
from itertools import chain
from multiprocessing import Process
from pathlib import Path
from random import randint
from socket import AF_UNIX, SOCK_SEQPACKET, socket
from threading import Thread
import sys
import time

from ascii_to_hid import *

# From https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/drivers/hid/hid-input.c?h=v6.11.8
unk = 0
hid_keyboard = [
	  0,  0,  0,  0, 30, 48, 46, 32, 18, 33, 34, 35, 23, 36, 37, 38,
	 50, 49, 24, 25, 16, 19, 31, 20, 22, 47, 17, 45, 21, 44,  2,  3,
	  4,  5,  6,  7,  8,  9, 10, 11, 28,  1, 14, 15, 57, 12, 13, 26,
	 27, 43, 43, 39, 40, 41, 51, 52, 53, 58, 59, 60, 61, 62, 63, 64,
	 65, 66, 67, 68, 87, 88, 99, 70,119,110,102,104,111,107,109,106,
	105,108,103, 69, 98, 55, 74, 78, 96, 79, 80, 81, 75, 76, 77, 71,
	 72, 73, 82, 83, 86,127,116,117,183,184,185,186,187,188,189,190,
	191,192,193,194,134,138,130,132,128,129,131,137,133,135,136,113,
	115,114,unk,unk,unk,121,unk, 89, 93,124, 92, 94, 95,unk,unk,unk,
	122,123, 90, 91, 85,unk,unk,unk,unk,unk,unk,unk,111,unk,unk,unk,
	unk,unk,unk,unk,unk,unk,unk,unk,unk,unk,unk,unk,unk,unk,unk,unk,
	unk,unk,unk,unk,unk,unk,179,180,unk,unk,unk,unk,unk,unk,unk,unk,
	unk,unk,unk,unk,unk,unk,unk,unk,unk,unk,unk,unk,unk,unk,unk,unk,
	unk,unk,unk,unk,unk,unk,unk,unk,111,unk,unk,unk,unk,unk,unk,unk,
	 29, 42, 56,125, 97, 54,100,126,164,166,165,163,161,115,114,113,
	150,158,159,128,136,177,178,176,142,152,173,140,unk,unk,unk,unk
]
evdev_keyboard = [0 for _ in range(0x100)]
for evdev_key,hid_key in enumerate(hid_keyboard):
    evdev_keyboard[hid_key] = evdev_key

def evdev_to_hid(key):
    return evdev_keyboard[key]




# Open connection sockets

base = Path(sys.argv[1])
print(f'Opening sockets at at {base}')

print('Creating socket')
interrupt = socket(family=AF_UNIX, type=SOCK_SEQPACKET)
print('Conncting')
interrupt.connect(bytes(base / 'interrupt'))
print('Connected')

def clamp8(v):
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

async def handle_key():

    for path in list_devices():
        key_dev = InputDevice(path)
        # Stop if we find a USB keyboard.
        if 'Keyboard' in key_dev.name and 'usb' in key_dev.phys and 'Control' not in key_dev.name:
            break
    print('Keyboard:', key_dev)

    key_dev.grab()

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
        0,
    ]

    async for event in key_dev.async_read_loop():
        if event.type != ecodes.EV_KEY:
            continue
        # Ignore repeats
        if event.value == 2:
            continue

        # Zero keys
        key_report[2:] = [0 for _ in key_report[2:]]

        # Set modifiers
        active_keys = key_dev.active_keys()
        modifiers = [
                ecodes.KEY_LEFTCTRL in active_keys,
                ecodes.KEY_LEFTSHIFT in active_keys,
                ecodes.KEY_LEFTALT in active_keys,
                ecodes.KEY_LEFTMETA in active_keys,
                ecodes.KEY_RIGHTCTRL in active_keys,
                ecodes.KEY_RIGHTSHIFT in active_keys,
                ecodes.KEY_RIGHTALT in active_keys,
                ecodes.KEY_RIGHTMETA in active_keys,
                ]
        key_report[2] = pack_bits(modifiers)

        # Set remaining active keys
        active_keys = [evdev_to_hid(key) for key in active_keys[:6]]
        key_report[4:4+len(active_keys)] = active_keys

        # Serialize and send report
        report_bytes = bytes(key_report)
        interrupt.send(report_bytes)


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

    for path in list_devices():
        mouse_dev = InputDevice(path)
        # Stop if we find a USB mouse.
        if 'Mouse' in mouse_dev.name and 'usb' in mouse_dev.phys:
            break
    print('Mouse:', mouse_dev)

    mouse_dev.grab()

    async for event in mouse_dev.async_read_loop():
        if event.type == ecodes.EV_SYN:
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
        if event.type == ecodes.EV_KEY:
            # Ignore duplicates
            if event.value == 2:
                continue
            if event.code == ecodes.BTN_TOUCH:
                mouse_state['btn'][0] = event.value

                # On release, clear absolute values
                if event.value == 0:
                    mouse_state['abs'][0] = None
                    mouse_state['abs'][1] = None

            # Mouse buttons
            if event.code == ecodes.BTN_LEFT:
                mouse_state['btn'][0] = event.value
            if event.code == ecodes.BTN_RIGHT:
                mouse_state['btn'][1] = event.value
            if event.code == ecodes.BTN_MIDDLE:
                mouse_state['btn'][2] = event.value

        # Touch movements
        if event.type == ecodes.EV_REL:
            if event.code in [0, 1]:
                mouse_state['rel'][event.code] = event.value
            if event.code in [ecodes.REL_WHEEL, ecodes.REL_WHEEL_HI_RES]:
                mouse_state['rel'][2] = event.value
    
        if event.type == ecodes.EV_ABS:
            # Touch movements
            axis = None
            if event.code == ecodes.ABS_MT_POSITION_X:
                axis = 0
            if event.code == ecodes.ABS_MT_POSITION_Y:
                axis = 1

            if axis is not None:
                if mouse_state['abs'][axis] is not None:
                    diff = event.value - mouse_state['abs'][axis]
                    mouse_state['rel'][axis] = diff

                mouse_state['abs'][axis] = event.value


async def main():
    async with asyncio.TaskGroup() as tg:
        key_task = tg.create_task(handle_key())
        mouse_task = tg.create_task(handle_mouse())

    print(key_task.result(), mouse_task.result())

asyncio.run(main())
