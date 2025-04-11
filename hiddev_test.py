#!/bin/env python3

# Advertise as a mouse, wait for a single device to connect, then send a series
# of twitch events.

import hid_server
import time

if __name__ == '__main__':
    server = hid_server.Server()
    
    with server.command_socket() as command_socket:
        with open('./sdp/mouse.xml', 'rb') as sdp_record:
            command_socket.up(sdp_record.read())
    
            print('Up')
        
        device = None
        with server.event_socket() as event_socket:
            while device is None:
                event = event_socket.read_event()
                print(f'Received event {event.__dict__}')
                if event.event == HDSEvent.INTERRUPT_LISTENING:
                    device = server.device(event.address)
    
    print('Down')
    
    with device.interrupt_socket() as interrupt:
        for _ in range(10):
            interrupt.send(b'\xa1\x02\x00\x40\x00')
            time.sleep(3e-1)
            interrupt.send(b'\xa1\x02\x00\xb0\x00')
            time.sleep(3e-1)
    
