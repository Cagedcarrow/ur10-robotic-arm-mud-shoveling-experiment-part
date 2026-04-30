#!/usr/bin/env python3
from __future__ import annotations

import struct
from typing import Dict, Optional

import serial

FT300_FRAME_SIZE = 16
FT300_HEADER = b"\x20\x4E"


def modbus_crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def build_fc16_start_stream(slave_id: int) -> bytes:
    payload = bytes([slave_id & 0xFF, 0x10, 0x01, 0x9A, 0x00, 0x01, 0x02, 0x02, 0x00])
    crc = modbus_crc16(payload)
    return payload + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


class FT300Reader:
    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 19200,
        timeout: float = 0.2,
        slave_id: int = 9,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.slave_id = slave_id
        self.ser: Optional[serial.Serial] = None
        self.buf = bytearray()
        self.fields = ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]

    def connect(self) -> bool:
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
            )
            self.buf.clear()
            self.ser.reset_input_buffer()
            self.ser.write(build_fc16_start_stream(self.slave_id))
            self.ser.flush()
            self.ser.read(64)
            return True
        except Exception:
            self.close()
            return False

    def close(self) -> None:
        if self.ser is not None:
            try:
                if self.ser.is_open:
                    self.ser.write(b"\xFF" * 50)
                    self.ser.flush()
                    self.ser.close()
            except Exception:
                pass
            finally:
                self.ser = None
        self.buf.clear()

    def _parse_frame(self, frame: bytes) -> Optional[Dict[str, float]]:
        if len(frame) != FT300_FRAME_SIZE:
            return None
        if frame[:2] != FT300_HEADER:
            return None
        crc_exp = frame[-2] | (frame[-1] << 8)
        crc_calc = modbus_crc16(frame[:-2])
        if crc_exp != crc_calc:
            return None
        raw = [struct.unpack_from("<h", frame, 2 + i * 2)[0] for i in range(6)]
        return {
            "Fx": raw[0] / 100.0,
            "Fy": raw[1] / 100.0,
            "Fz": raw[2] / 100.0,
            "Mx": raw[3] / 1000.0,
            "My": raw[4] / 1000.0,
            "Mz": raw[5] / 1000.0,
        }

    def read_sample(self) -> Optional[Dict[str, float]]:
        if self.ser is None or not self.ser.is_open:
            return None
        try:
            incoming = self.ser.read(256)
        except Exception:
            return None
        if incoming:
            self.buf.extend(incoming)
        if len(self.buf) > 4096:
            self.buf = self.buf[-256:]

        while len(self.buf) >= FT300_FRAME_SIZE:
            idx = self.buf.find(FT300_HEADER)
            if idx < 0:
                self.buf = self.buf[-1:]
                return None
            if idx > 0:
                del self.buf[:idx]
            if len(self.buf) < FT300_FRAME_SIZE:
                return None
            frame = bytes(self.buf[:FT300_FRAME_SIZE])
            del self.buf[:FT300_FRAME_SIZE]
            parsed = self._parse_frame(frame)
            if parsed is not None:
                return parsed
        return None
