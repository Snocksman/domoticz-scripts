#!/usr/bin/python

# Note: Python 2.7 for compliance with Domoticz & FHEM

# Full color support ( hex, RGB and HSV )
# Full brightness support ( 0 - 100 )
# Full saturation support ( 0 - 100 )
# Full device and zone support

# Usage:
#  milight-home.py [DEVICE (0,1,7,8)] [ZONE (0,1,2,3,4)] [COMMAND ...]
#
# Commands are:
#  ON
#  OFF
#  DIMUP                        Only for Device type 1
#  DIMDOWN                      Only for Device type 1
#  NIGHT                        Nightlight for Device type 1 & 8
#  DISCO[1-9]
#  DISCOFASTER
#  DISCOSLOWER
#  WHITE                        for Device type 0 & 8
#  TEMP (0-100)                 White-Temperature for Device type 8
#  HUE (0-255)
#  SATUR (0-100)
#  BRIGHT (0-100)
#  SPECTRUM                     Animates lamps through full color spectrum
#  COLOR "(hex color)"          ie. "#ff0000" for red, "#0000ff" for blue ('#' char not needed)
#  COLOR (red) (green) (blue)   ie. 255 0 0 for red, 0 0 255 for blue

__author__ = 'Jasper Goes (Pander) & Mathias Klein (Snocksman)'
__email__ = "jasper@jaspergoes.nl & snocksman@t-online.de"

# Optional configuration
BOX_REPT = 1  # Amount of times to repeat commands
BOX_DISCOVERY = False  # Auto-discover BOX_ADDR
BOX_ADDR = "192.168.1.11"  # IP Address of iBox. To use this, set: BOX_DISCOVERY = False
BOX_PORT = 5987  # iBox port. Should not need any modification.

# For basic usage, no further modification is nescessary beyond this line
import re
import sys
import array
import socket
from time import sleep
from colorsys import rgb_to_hsv

NOONCE = 1
LCL_PORT = 55054
SESSPW = bytearray([255, 255])

def usage():
    print "Please specify a valid argument.\n\nUsage:\n milight-home.py [DEVICE (0,1,7,8)] [ZONE (0,1,2,3,4)] " \
          "[COMMAND ...]\n\nCommands are:\n ON\n OFF\n DISCO[1-9]\n DISCOFASTER\n DISCOSLOWER\n WHITE\n BRIGHT " \
          "(0-100)\n SPECTRUM\t\t\t\t\t\tAnimates lamps through full color spectrum\n COLOR \"(hex color)\"\t" \
          "\t\tie. \"#ff0000\" for red, \"#0000ff\" for blue\n COLOR (red) (green) (blue)\tie. 255 0 0 for red, 0 0 " \
          "255 for blue"
    raise SystemExit(1)

def build(payload):
    global NOONCE, SESSID, SESSPW
    NOONCE = (NOONCE + 1) % 256
    # Base frame
    frame = [128, 0, 0, 0, 17, 0, NOONCE, 0, 49, 0, 0]
    # Session
    frame[5:5] = SESSID
    # Password
    frame[11:11] = SESSPW
    # Payload
    frame[13:13] = payload
    # Checksum
    frame[21] = sum(frame[i] for i in range(10, 20)) % 256
    return bytearray(frame)

def hex_to_milight_color(v):
    v = v.lstrip('#')
    l = len(v)
    r, g, b = (int(v[i:i + l // 3], 16) for i in range(0, l, l // 3))
    return rgb_to_milight_color(r, g, b)

def rgb_to_milight_color(r, g, b):
    return int(float(tuple(rgb_to_hsv(float(r) / 255, float(g) / 255, float(b) / 255))[0]) * 256)

# Check if sufficient arguments are passed
if len(sys.argv) < 4:
    usage()

DEVICE = int(sys.argv[1])
if DEVICE < 0 or DEVICE > 8:
    print "[ERROR] Invalid device. Device can be any of 0, 7 or 8. Given:", DEVICE, "\n"
    usage()

ZONE = int(sys.argv[2])
if ZONE < 0 or ZONE > 4:
    print "[ERROR] Invalid zone. Zone can be any of 0, 1, 2, 3 or 4. Given:", ZONE, "\n"
    usage()

CMD = sys.argv[3].upper()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('', LCL_PORT))
sock.settimeout(2)

# Acknowledge the first milight device on the network to respond
if BOX_DISCOVERY:
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    success = False
    for i in range(0, 4):
        sock.sendto(bytearray('HF-A11ASSISTHREAD', 'utf-8'), ('255.255.255.255', 48899))
        try:
            data = tuple(sock.recvfrom(64))[0]
            if len(data) == 34:
                BOX_ADDR = data.decode('utf-8').split(',')[0]
                success = True
                break
        except socket.timeout:
            continue

    if not success:
        print "[ERROR] iBox discovery did not return any results."
        raise SystemExit(1)

sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
success = False
for i in range(0, 4):
    sock.sendto(bytearray(
        [32, 0, 0, 0, 22, 2, 98, 58, 213, 237, 163, 1, 174, 8, 45, 70, 97, 65, 167, 246, 220, 175, 211, 230, 0, 0, 30]),
        (BOX_ADDR, BOX_PORT))
    try:
        data = tuple(sock.recvfrom(64))[0]
        if str(data.encode('hex')).startswith('2800000011'):
            SESSID = [data[19], data[20]]
            success = True
            break
    except socket.timeout:
        continue

if not success:
    sock.close()
    print "[ERROR] Did not receive the expected response from iBox"
    raise SystemExit(2)

success = False
for i in range(0, 4):
    if not success:
        sock.sendto(build([0, 1, 0, 0, 0, 0, 0]), (BOX_ADDR, BOX_PORT))

        for x in range(0, 2):
            try:
                data = tuple(sock.recvfrom(64))[0]
                if str(data.encode('hex')).startswith('8000000015'):
                    data = array.array('B', data)
                    SESSPW = [data[16], data[17]]
                    print "[DEBUG] Found iBox password to be", str(data[16]).zfill(2), str(data[17]).zfill(2)
                    success = True
                    break
            except socket.timeout:
                continue

if not success:
    sock.close()
    print "[ERROR] Could not discover password bytes from iBox"
    raise SystemExit(2)

# Prepare the message to send
if CMD == "ON":
    if DEVICE == 0:
        COMMAND = [0, 3, 3, 0, 0, 0, 0]
    else:
        if DEVICE == 1:
            COMMAND = [DEVICE, 0, 7, 0, 0, 0, ZONE]
        else:
            if DEVICE == 8:
                COMMAND = [DEVICE, 4, 1, 0, 0, 0, ZONE]
            else:
                COMMAND = [DEVICE, 3, 1, 0, 0, 0, ZONE]

elif CMD == "OFF":
    if DEVICE == 0:
        COMMAND = [0, 3, 4, 0, 0, 0, 0]
    else:
        if DEVICE == 1:
            COMMAND = [DEVICE, 0, 8, 0, 0, 0, ZONE]
        else:
            if DEVICE == 8:
                COMMAND = [DEVICE, 4, 2, 0, 0, 0, ZONE]
            else:
                COMMAND = [DEVICE, 3, 2, 0, 0, 0, ZONE]

elif CMD == "DIMUP":
    if DEVICE == 1:
        COMMAND = [DEVICE, 0, 1, 0, 0, 0, ZONE]
    else:
        print "DIMUP command only supported by device type 1."

elif CMD == "DIMDOWN":
    if DEVICE == 1:
        COMMAND = [DEVICE, 0, 2, 0, 0, 0, ZONE]
    else:
        print "DIMDOWN command only supported by device type 1."

elif CMD == "NIGHT":
    if DEVICE == 1:
        COMMAND = [DEVICE, 0, 6, 0, 0, 0, ZONE]
    else:
        if DEVICE == 8:
            COMMAND = [DEVICE, 4, 5, 0, 0, 0, ZONE]
        else:
            print "NIGHT command only supported by device Type 1 & 8."
            
elif CMD == "DISCOFASTER":
    if DEVICE == 0:
        COMMAND = [DEVICE, 3, 2, 0, 0, 0, 0]
    elif DEVICE == 7:
        COMMAND = [DEVICE, 3, 3, 0, 0, 0, ZONE]
    elif DEVICE == 8:
        COMMAND = [DEVICE, 4, 3, 0, 0, 0, ZONE]

elif CMD == "DISCOSLOWER":
    if DEVICE == 0:
        COMMAND = [DEVICE, 3, 1, 0, 0, 0, 0]
    elif DEVICE == 7:
        COMMAND = [DEVICE, 3, 4, 0, 0, 0, ZONE]
    elif DEVICE == 8:
        COMMAND = [DEVICE, 4, 4, 0, 0, 0, ZONE]

elif CMD.startswith("DISCO"):
    i = max(1, min(9, int(CMD[5])))
    if DEVICE == 7 or DEVICE == 0:
        COMMAND = [DEVICE, 4, i, 0, 0, 0, ZONE]
    elif DEVICE == 8:
        COMMAND = [DEVICE, 6, i, 0, 0, 0, ZONE]

elif CMD == "WHITE":
    if DEVICE == 0:
        COMMAND = [DEVICE, 3, 5, 0, 0, 0, ZONE]
    else:
        if DEVICE == 8:
            COMMAND = [DEVICE, 5, 64, 0, 0, 0, ZONE]
        else:
            print "WHITE command only supported by device Type 0 & 8."

elif CMD == "TEMP":
    if len(sys.argv) == 5:
        if DEVICE ==8:
            COMMAND = [DEVICE, 5, max(0, min(100, int(sys.argv[4]))), 0, 0, 0, ZONE]
    else:
        sock.close()
        print "No value for White-Temperature given. Add a 0 - 100 value for Temperature.\n"
        usage()

elif CMD == "HUE":
    if len(sys.argv) == 5:
        if DEVICE == 8:
            HUE = max(0, min(255, int(sys.argv[4])))
            COMMAND = [DEVICE, 1, HUE, HUE, HUE, HUE, ZONE]
    else:
        sock.close()
        print "No value for HUE given. Add a 0 - 255 value for HUE.\n"
        usage()

elif CMD == "SATUR":
    if len(sys.argv) == 5:
        if DEVICE ==8:
            COMMAND = [DEVICE, 2, max(0, min(100, int(sys.argv[4]))), 0, 0, 0, ZONE]
    else:
        sock.close()
        print "No value for saturation given. Add a 0 - 100 value for saturation.\n"
        usage()

elif CMD == "BRIGHT":
    if len(sys.argv) == 5:
        if DEVICE == 8:
            COMMAND = [DEVICE, 3, max(0, min(100, int(sys.argv[4]))), 0, 0, 0, ZONE]
        else:
            COMMAND = [DEVICE, 2, max(0, min(100, int(sys.argv[4]))), 0, 0, 0, ZONE]
    else:
        sock.close()
        print "No value for brightness given. Add a 0 - 100 value for brightness.\n"
        usage()        

elif CMD == "COLOR":
    if len(sys.argv) == 5 and re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', sys.argv[4]):
        COLOR = hex_to_milight_color(sys.argv[4])
        if DEVICE == 7:
            COLOR = (COLOR + 26) % 256
        elif DEVICE == 8:
            COLOR = (COLOR + 10) % 256
        COMMAND = [DEVICE, 1, COLOR, COLOR, COLOR, COLOR, ZONE]
    elif len(sys.argv) == 7:
        r = max(0, min(255, int(sys.argv[4])))
        g = max(0, min(255, int(sys.argv[5])))
        b = max(0, min(255, int(sys.argv[6])))
        COLOR = rgb_to_milight_color(r, g, b)
        if DEVICE == 7:
            COLOR = (COLOR + 26) % 256
        elif DEVICE == 8:
            COLOR = (COLOR + 10) % 256
        COMMAND = [DEVICE, 1, COLOR, COLOR, COLOR, COLOR, ZONE]
    else:
        sock.close()
        print "No (correct) value for color given. May be hex (ie. \"#ff0000\" or \"#00ff00\" etc etc), or RGB values (ie. 255 0 0 or 0 255 0). Add a valid value for color.\n"
        usage()

elif CMD == "SPECTRUM":
    print "[DEBUG] Communicating with iBox at " + BOX_ADDR + ", identified by ID", SESSID[0].encode('hex').upper(), \
        SESSID[1].encode('hex').upper()
    for i in range(0, 256):
        if DEVICE == 7:
            COLOR = (i + 26) % 256
        elif DEVICE == 8:
            COLOR = (i + 10) % 256
        COMMAND = [DEVICE, 1, COLOR, COLOR, COLOR, COLOR, ZONE]
        for z in range(0, max(1, BOX_REPT)):
            payload = build(COMMAND)
            sock.sendto(payload, (BOX_ADDR, BOX_PORT))
            hex = ''.join(format(x, '02x') for x in payload).upper()
            print "[DEBUG] Sending message to the iBox:       " + ' '.join(
                hex[i:i + 2] for i in range(0, len(hex), 2)), "Color", COLOR

            # Wait 10 milliseconds before re-sending the payload
            # This gives the ibox time to propagate any previous command(s) over RF
            if BOX_REPT > 1 and z < BOX_REPT:
                sleep(0.01)

        # Wait 300 milliseconds before next color (Duration is (255 * 0.3)+((BOX_REPT - 1) * 0.1) seconds)
        sleep(0.3)

    print "[DEBUG] Messages sent!"

    raise SystemExit(0)

else:
    usage()

print "[DEBUG] Communicating with iBox at " + BOX_ADDR + ", identified by ID", SESSID[0].encode('hex').upper(), \
    SESSID[1].encode('hex').upper()
for i in range(0, max(1, BOX_REPT)):
    payload = build(COMMAND)
    sock.sendto(payload, (BOX_ADDR, BOX_PORT))
    hex = ''.join(format(x, '02x') for x in payload).upper()
    print "[DEBUG] Sending message to the iBox:       " + ' '.join(hex[i:i + 2] for i in range(0, len(hex), 2))

    # Wait 10 milliseconds before re-sending the payload
    # This gives the ibox time to propagate any previous command(s) over RF
    if BOX_REPT > 1 and i < BOX_REPT:
        sleep(0.01)

sock.close()

print "[DEBUG] Message sent!"

raise SystemExit(0)
