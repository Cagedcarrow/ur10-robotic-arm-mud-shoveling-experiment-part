#!/usr/bin/env python3
import argparse
import binascii
import struct
import time

import serial


def modbus_crc(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def build_fc03(slave_id: int, register: int, byte_count: int) -> bytes:
    words = (byte_count + 1) // 2 if byte_count % 2 else byte_count // 2
    frame = bytes(
        [
            slave_id,
            0x03,
            (register >> 8) & 0xFF,
            register & 0xFF,
            (words >> 8) & 0xFF,
            words & 0xFF,
        ]
    )
    crc = modbus_crc(frame)
    return frame + struct.pack("<H", crc)


def hexdump(data: bytes) -> str:
    return binascii.hexlify(data, sep=" ").decode("ascii")


def try_read_firmware(ser: serial.Serial, slave_id: int = 9) -> None:
    request = build_fc03(slave_id=slave_id, register=500, byte_count=2)
    ser.reset_input_buffer()
    ser.write(request)
    ser.flush()
    time.sleep(0.1)
    response = ser.read(64)
    print(f"modbus_request: {hexdump(request)}")
    if response:
        print(f"modbus_response_raw: {response!r}")
        print(f"modbus_response_hex: {hexdump(response)}")
    else:
        print("modbus_response_raw: <no response>")


def main() -> int:
    parser = argparse.ArgumentParser(description="Minimal FT300 raw serial probe")
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--baudrate", type=int, default=19200)
    parser.add_argument("--duration", type=float, default=5.0)
    args = parser.parse_args()

    print(f"opening port={args.port} baudrate={args.baudrate} duration={args.duration}")
    with serial.Serial(args.port, args.baudrate, timeout=0.2) as ser:
        print("serial_opened")
        try_read_firmware(ser)
        start = time.time()
        while time.time() - start < args.duration:
            chunk = ser.read(256)
            if chunk:
                print(f"raw_bytes: {chunk!r}")
                print(f"raw_hex: {hexdump(chunk)}")
            else:
                print("raw_bytes: <timeout>")
            time.sleep(0.1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
