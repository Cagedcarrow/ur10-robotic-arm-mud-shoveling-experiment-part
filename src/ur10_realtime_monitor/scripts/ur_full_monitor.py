#!/usr/bin/env python3
from __future__ import annotations

import socket
import struct
from typing import List, Optional


class URFullMonitor:
    def __init__(self, robot_ip: str = "10.160.9.21", port: int = 30003) -> None:
        self.robot_ip = robot_ip
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.header = [
            "Time",
            "Act_q0",
            "Act_q1",
            "Act_q2",
            "Act_q3",
            "Act_q4",
            "Act_q5",
            "Act_qd0",
            "Act_qd1",
            "Act_qd2",
            "Act_qd3",
            "Act_qd4",
            "Act_qd5",
            "Act_I0",
            "Act_I1",
            "Act_I2",
            "Act_I3",
            "Act_I4",
            "Act_I5",
            "Act_X",
            "Act_Y",
            "Act_Z",
            "Act_RX",
            "Act_RY",
            "Act_RZ",
            "Act_dX",
            "Act_dY",
            "Act_dZ",
            "Act_dRX",
            "Act_dRY",
            "Act_dRZ",
            "Tgt_q0",
            "Tgt_q1",
            "Tgt_q2",
            "Tgt_q3",
            "Tgt_q4",
            "Tgt_q5",
            "Robot_Mode",
            "Safety_Mode",
            "Main_Voltage",
            "Robot_Voltage",
            "Robot_Current",
            "Label",
        ]

    def connect(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(3)
            self.socket.connect((self.robot_ip, self.port))
            return True
        except Exception as exc:
            print(f"[URFullMonitor] connect failed: {exc}")
            self.close()
            return False

    def close(self) -> None:
        if self.socket is not None:
            try:
                self.socket.close()
            except Exception:
                pass
            finally:
                self.socket = None

    def recv_exactly(self, nbytes: int) -> Optional[bytes]:
        if self.socket is None:
            return None
        chunks = bytearray()
        while len(chunks) < nbytes:
            try:
                chunk = self.socket.recv(nbytes - len(chunks))
            except socket.timeout:
                return None
            except Exception:
                return None
            if not chunk:
                return None
            chunks.extend(chunk)
        return bytes(chunks)

    def read_packet(self) -> Optional[bytes]:
        if self.socket is None:
            return None
        header = self.recv_exactly(4)
        if header is None or len(header) < 4:
            return None
        packet_len = struct.unpack("!i", header)[0]
        if packet_len <= 4 or packet_len > 10000:
            return None
        body = self.recv_exactly(packet_len - 4)
        if body is None:
            return None
        return header + body

    def parse_packet(self, data: bytes) -> Optional[List[float]]:
        try:
            if len(data) < 1028:
                return None

            # Common UR 30003 offsets:
            # Time: data[4:12]
            # Tgt_q: data[12:60]
            # Act_q: data[252:300]
            # Act_qd: data[300:348]
            # Act_I: data[348:396]
            # Act_TCP_Pose: data[444:492]
            # Act_TCP_Speed: data[492:540]
            # Robot_Mode: data[756:764]
            # Safety_Mode: data[812:820]
            # Main_Voltage: data[1004:1012]
            # Robot_Voltage: data[1012:1020]
            # Robot_Current: data[1020:1028]
            row: List[float] = [struct.unpack("!d", data[4:12])[0]]
            row.extend(struct.unpack("!6d", data[252:300]))
            row.extend(struct.unpack("!6d", data[300:348]))
            row.extend(struct.unpack("!6d", data[348:396]))
            row.extend(struct.unpack("!6d", data[444:492]))
            row.extend(struct.unpack("!6d", data[492:540]))
            row.extend(struct.unpack("!6d", data[12:60]))
            row.append(struct.unpack("!d", data[756:764])[0])
            row.append(struct.unpack("!d", data[812:820])[0])
            row.append(struct.unpack("!d", data[1004:1012])[0])
            row.append(struct.unpack("!d", data[1012:1020])[0])
            row.append(struct.unpack("!d", data[1020:1028])[0])
            return row
        except Exception as exc:
            print(f"[URFullMonitor] parse error: {exc}")
            return None
