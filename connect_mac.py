#!/bin/env python3

import asyncio
from pathlib import Path
from socket import AF_UNIX, socket, SOCK_DGRAM, SOCK_SEQPACKET
import subprocess
import sys
from threading import Thread

base_path = Path(sys.argv[1])
command = sys.argv[2]
command_args = sys.argv[3:]

BUFSIZE = 1024

HIDP_HANDSHAKE = 0x0
HIDP_HID_CONTROL = 0x1
HIDP_GET_REPORT = 0x4
HIDP_SET_REPORT = 0x5
HIDP_GET_PROTOCOL = 0x6
HIDP_SET_PROTOCOL = 0x7
HIDP_DATA = 0xA

HANDSHAKE_SUCCESSFUL = 0x0
HANDSHAKE_NOT_READY = 0x1
HANDSHAKE_ERR_INVALID_REPORT_ID = 0x2
HANDSHAKE_ERR_UNSUPPORTED_REQUEST = 0x3
HANDSHAKE_INVALID_PARAMETER = 0x4
HANDSHAKE_UNKNOWN = 0xE
HANDSHAKE_FATAL = 0xF

def new_handshake(param):
    return bytes([HIDP_HANDSHAKE << 4 | param])

EVENT_LAGGED = 0x01
EVENT_CONTROL_LISTENING = 0x02
EVENT_INTERRUPT_LISTENING = 0x03
EVENT_DISCONNECTED = 0x04

def addr_to_path(addr):
    return base_path / '_'.join(f'{b:02X}' for b in addr)

def handle_control(addr):
    conn_path = addr_to_path(addr)
    print(f'Connecting to {conn_path}')

    with socket(AF_UNIX, SOCK_SEQPACKET) as control_socket:
        control_socket.connect(bytes(conn_path / 'control'))
        print('Control connected')
        while True:
            # Receive control message
            buf = control_socket.recv(BUFSIZE)
            if len(buf) == 0:
                print('Control msg with len 0')
                break
            # Parse opcode and param from the first byte
            opcode = (buf[0] >> 4) & 0xF
            param = buf[0] & 0xF

            # Parse command based on opcode
            if opcode == HIDP_HANDSHAKE:
                print('Handshake')
            elif opcode == HIDP_HID_CONTROL:
                print('HID control')
            elif opcode == HIDP_GET_REPORT:
                print('Get report')
            elif opcode == HIDP_SET_REPORT:
                print('Set report')
            elif opcode == HIDP_GET_PROTOCOL:
                print('Get protocol')
            elif opcode == HIDP_SET_PROTOCOL:
                print('Set protocol')
                # Reply with success
                control_socket.send(new_handshake(HANDSHAKE_SUCCESSFUL))
                print('Reply with handshake')
            elif opcode == HIDP_DATA:
                print('Data')
            else:
                print(f'Misc control message: {opcode} {param}')

def handle_interrupt(addr):
    conn_path = addr_to_path(addr)
    print(f'Connecting to interrupt at {conn_path}', flush=True)

    args = [command, *command_args, conn_path.resolve()]
    print(f'Running command {args}')

    # Launch subprogram
    subprocess.run(args, capture_output=True);

def main():
    # Main loop
    with socket(AF_UNIX, SOCK_SEQPACKET) as event_socket:
        event_socket.connect(bytes(base_path / 'event'))
    
        while True:
            # Receive event
            buf = event_socket.recv(BUFSIZE)
            if len(buf) < 1:
                print('Received empty event')
                break
            # Parse event
            if buf[0] == EVENT_CONTROL_LISTENING:
                if len(buf) != 7:
                    print('Wrong length for control connect event')
                    break
    
                addr = buf[1:]
    
                # Handle new control connection
                th = Thread(target=handle_control, args=(addr,))
                th.start()
            elif buf[0] == EVENT_INTERRUPT_LISTENING:
                if len(buf) != 7:
                    print('Wrong length for control connect event')
                    break

                addr = buf[1:]
    
                # Start a new process to handle the socket
                th = Thread(target=handle_interrupt, args=(addr,))
                th.start()

main()
