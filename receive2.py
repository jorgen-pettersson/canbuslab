import serial
import string
import binascii
import json
import datetime
from CanBusLogPersistor import CanBusLogPersistor
import queue
import threading
import argparse

strFrameType = ""
strFrameFormat = ""
len2 = 0
id = 0
print("The converter is equipped with two built - in conversion protocols, \none is a fixed 20 byte protocol and the other is a variable length protocol. \nPlease ensure that the variable length protocol is selected in the supporting software \nand click the Set and Start button to issue a configuration command to the converter")


log_queue = queue.Queue(maxsize=10000)
stop_event = threading.Event()
#set_can_baudrate = []

configs = {
}

configs["default"] = [
        0xaa,     #  0  Packet header
        0x55,     #  1  Packet header
        0x12,     #  3 Type: use variable protocol to send and receive data##  0x02- Setting (using fixed 20 byte protocol to send and receive data),   0x12- Setting (using variable protocol to send and receive data)##
        0x01,     #  3 CAN Baud Rate:  0x03 500kbps  ##  0x01(1Mbps),  0x02(800kbps),  0x03(500kbps),  0x04(400kbps),  0x05(250kbps),  0x06(200kbps),  0x07(125kbps),  0x08(100kbps),  0x09(50kbps),  0x0a(20kbps),  0x0b(10kbps),   0x0c(5kbps)##
        0x02,     #  4  Frame Type: Extended Frame  ##   0x01 standard frame,   0x02 extended frame ##
        0x00,     #  5  Filter ID1
        0x00,     #  6  Filter ID2
        0x00,     #  7  Filter ID3
        0x00,     #  8  Filter ID4
        0x00,     #  9  Mask ID1
        0x00,     #  10 Mask ID2
        0x00,     #  11 Mask ID3
        0x00,     #  12 Mask ID4
        0x00,     #  13 CAN mode:  normal mode  ##   0x00 normal mode,   0x01 silent mode,   0x02 loopback mode,   0x03 loopback silent mode ##
        0x00,     #  14 automatic resend:  automatic retransmission
        0x00,     #  15 Spare
        0x00,     #  16 Spare
        0x00,     #  17 Spare
        0x00,     #  18 Spare
    ]

configs["local_rpi"] = [
        0xaa,     #  0  Packet header
        0x55,     #  1  Packet header
        0x12,     #  3 Type: use variable protocol to send and receive data##  0x02- Setting (using fixed 20 byte protocol to send and receive data),   0x12- Setting (using variable protocol to send and receive data)##
        0x01,     #  3 CAN Baud Rate:  0x03 500kbps  ##  0x01(1Mbps),  0x02(800kbps),  0x03(500kbps),  0x04(400kbps),  0x05(250kbps),  0x06(200kbps),  0x07(125kbps),  0x08(100kbps),  0x09(50kbps),  0x0a(20kbps),  0x0b(10kbps),   0x0c(5kbps)##
        0x02,     #  4  Frame Type: Extended Frame  ##   0x01 standard frame,   0x02 extended frame ##
        0x00,     #  5  Filter ID1
        0x00,     #  6  Filter ID2
        0x00,     #  7  Filter ID3
        0x00,     #  8  Filter ID4
        0x00,     #  9  Mask ID1
        0x00,     #  10 Mask ID2
        0x00,     #  11 Mask ID3
        0x00,     #  12 Mask ID4
        0x00,     #  13 CAN mode:  normal mode  ##   0x00 normal mode,   0x01 silent mode,   0x02 loopback mode,   0x03 loopback silent mode ##
        0x01,     #  14 automatic resend:  automatic retransmission
        0x00,     #  15 Spare
        0x00,     #  16 Spare
        0x00,     #  17 Spare
        0x00,     #  18 Spare
    ]

#TOYOTA
configs["toyota"] = [
        0xaa,     #  0  Packet header
        0x55,     #  1  Packet header
        0x12,     #  3 Type: use variable protocol to send and receive data##  0x02- Setting (using fixed 20 byte protocol to send and receive data),   0x12- Setting (using variable protocol to send and receive data)##
        0x03,     #  3 CAN Baud Rate:  0x03 500kbps  ##  0x01(1Mbps),  0x02(800kbps),  0x03(500kbps),  0x04(400kbps),  0x05(250kbps),  0x06(200kbps),  0x07(125kbps),  0x08(100kbps),  0x09(50kbps),  0x0a(20kbps),  0x0b(10kbps),   0x0c(5kbps)##
        0x02,     #  4  Frame Type: Extended Frame  ##   0x01 standard frame,   0x02 extended frame ##
        0x00,     #  5  Filter ID1
        0x00,     #  6  Filter ID2
        0x00,     #  7  Filter ID3
        0x00,     #  8  Filter ID4
        0x00,     #  9  Mask ID1
        0x00,     #  10 Mask ID2
        0x00,     #  11 Mask ID3
        0x00,     #  12 Mask ID4
        0x01,     #  13 CAN mode:  normal mode  ##   0x00 normal mode,   0x01 silent mode,   0x02 loopback mode,   0x03 loopback silent mode ##
        0x01,     #  14 automatic resend:  automatic retransmission
        0x00,     #  15 Spare
        0x00,     #  16 Spare
        0x00,     #  17 Spare
        0x00,     #  18 Spare
    ]

def calculate_checksum(data):
    ##    Check Summing
    checksum = sum(data[2:])
    return checksum & 0xff

def calculate_checksumV2(data):
    return sum(data) & 0xff

def read_exact(ser, n):
    data = ser.read(n)
    if len(data) != n:
        return None
    return data

persistor = CanBusLogPersistor(
    dsn="postgresql://dev:dev@localhost:5432/compensationcalculation",
    schema="compensationcalculation"
)


#Set the CAN speed section, in this example set to 500kbps, using a variable length transceiver
def init(serial_port):
    ser = serial.Serial(serial_port, 2000000)
    print(ser.portstr)
    return ser

def getCoonfig(name):
    return configs.get(name)

## END init    

def setBaudrate(set_can_baudrate,serial_port):
    #Calculate the checksum
    checksum = calculate_checksumV2(set_can_baudrate)
    set_can_baudrate.append(checksum)
    set_can_baudrate = bytes(set_can_baudrate)

    #Send command to set CAN baud rate
    #serial_port.write(set_can_baudrate)
    #print("CAN baud rate setting command sent.")
## END setBaudrate

def frame_is_complete(frame: bytearray) -> bool:
    if len(frame) < 2:
        return False

    # Command/config reply frame: AA 55 ... checksum, fixed 20 bytes
    if frame[0] == 0xAA and frame[1] == 0x55:
        return len(frame) == 20

    # CAN receive frame: AA Cx/Ex ... 55
    if frame[0] == 0xAA and (frame[1] & 0xC0) == 0xC0:
        dlc = frame[1] & 0x0F
        is_extended = (frame[1] & 0x20) != 0

        expected_len = 2 + (4 if is_extended else 2) + dlc + 1
        return len(frame) == expected_len and frame[-1] == 0x55

    return False


def read_frame(ser, max_len=64):
    frame = bytearray()

    while True:
        b = ser.read(1)
        if not b:
            continue

        byte = b[0]

        # Sync: first byte must be AA
        if not frame:
            if byte != 0xAA:
                continue

        frame.append(byte)

        if len(frame) > max_len:
            frame.clear()
            continue

        if frame_is_complete(frame):
            return bytes(frame)

        # If second byte is invalid, resync
        if len(frame) == 2:
            if not (
                frame[1] == 0x55 or
                (frame[1] & 0xC0) == 0xC0
            ):
                frame.clear()

def parse_can_frame(frame: bytes):
    if frame[0] != 0xAA:
        return None

    flags = frame[1]

    if (flags & 0xC0) != 0xC0:
        return None

    dlc = flags & 0x0F
    is_remote = (flags & 0x10) != 0
    is_extended = (flags & 0x20) != 0

    if is_extended:
        raw_id = frame[2:6]
        payload = frame[6:6 + dlc]
        can_id = (
            raw_id[0]
            | (raw_id[1] << 8)
            | (raw_id[2] << 16)
            | (raw_id[3] << 24)
        )
    else:
        raw_id = frame[2:4]
        payload = frame[4:4 + dlc]
        can_id = raw_id[0] | (raw_id[1] << 8)

    return {
        "timeStamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "canId": hex(can_id),
        "dlc": dlc,
        "data": [f"0x{x:02x}" for x in payload],
        "frameType": "Extended Frame" if is_extended else "Standard Frame",
        "frameFormat": "Remote Frame" if is_remote else "Data Frame",
        "raw": frame.hex(" "),
    }


def listen(serial_port):
    print("Start listening for CAN messages...")
    #with open("data.jsonl", "a") as f:
    # Read data from serial port
    while True:
        frame = read_frame(serial_port)

        parsed = parse_can_frame(frame)
        if parsed is None:
            continue
        if printConsole:
            print("Received frame:", parsed)        
        log_queue.put(parsed)


def writer_thread():
    batch = []

    #with open("data.jsonl", "a", buffering=1) as f:
    while not stop_event.is_set() or not log_queue.empty():
        try:
            item = log_queue.get(timeout=0.5)
            batch.append(item)
        except queue.Empty:
            pass

        if len(batch) >= 10:
            #f.write("".join(json.dumps(x) + "\n" for x in batch))
            for item in batch:    
                persistor.add(item)
            batch.clear()

    if batch:
        for item in batch:    
            persistor.add(item)


## Main execution
parser = argparse.ArgumentParser()
parser.add_argument("-c","--config", required=False,type=str,default="default", choices=configs.keys(), help="Select the configuration to use")
parser.add_argument("-o","--output", required=False, type=bool, default=False)
parser.add_argument("-s","--serial", required=False, type=str, default="/dev/ttyUSB0", help="Serial port to use, e.g. /dev/ttyUSB0")
args = parser.parse_args()


printConsole = False
if(args.output):
    printConsole = True
    
serial_port = args.serial    


set_can_baudrate=getCoonfig(args.config)
serial_port = init(serial_port)
setBaudrate(set_can_baudrate, serial_port)

t = threading.Thread(target=writer_thread)
t.start()

try:
    listen(serial_port)
finally:
    print("Stopping... ")
    try:
        stop_event.set()
        print("Stop event set, waiting for log queue to flush...")
        log_queue.join()
        print("Waiting for log queue to flush...")
        writer_thread.join()
        print("Waiting for writer thread to finish...")
        print("Log flushed")
    except Exception as e:
        print("Error while stopping:", e)
    
    # Close serial port
    # ser.close()