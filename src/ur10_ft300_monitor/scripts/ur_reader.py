#!/usr/bin/env python3
from __future__ import annotations

import socket
import struct
from typing import Dict, Optional


class URReader:
    def __init__(self, robot_ip: str = "10.160.9.21", port: int = 30003, timeout: float = 3.0) -> None:
        self.robot_ip = robot_ip
        self.port = port
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None
        self.fields = [
            "Time",
            *[f"Act_q{i}" for i in range(6)],
            *[f"Act_qd{i}" for i in range(6)],
            *[f"Act_I{i}" for i in range(6)],
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
            *[f"Tgt_q{i}" for i in range(6)],
            "Robot_Mode",
            "Safety_Mode",
            "Main_Voltage",
            "Robot_Voltage",
            "Robot_Current",
        ]

    def connect(self) -> bool:
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.robot_ip, self.port))
            return True
        except Exception:
            self.close()
            return False

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:
                pass
            finally:
                self.sock = None

    def _recv_exact(self, nbytes: int) -> Optional[bytes]:
        if self.sock is None:
            return None
        buf = bytearray()
        while len(buf) < nbytes:
            try:
                chunk = self.sock.recv(nbytes - len(buf))
            except Exception:
                return None
            if not chunk:
                return None
            buf.extend(chunk)
        return bytes(buf)

    def read_packet(self) -> Optional[bytes]:
        head = self._recv_exact(4)
        if head is None or len(head) < 4:
            return None
        p_len = struct.unpack("!i", head)[0]
        if p_len <= 4 or p_len > 10000:
            return None
        body = self._recv_exact(p_len - 4)
        if body is None:
            return None
        return head + body

    def parse_packet(self, data: bytes) -> Optional[Dict[str, float]]:
        try:
            if len(data) < 1028:
                return None
            row = {}
            row["Time"] = struct.unpack("!d", data[4:12])[0]

            act_q = struct.unpack("!6d", data[252:300])
            act_qd = struct.unpack("!6d", data[300:348])
            act_i = struct.unpack("!6d", data[348:396])
            tcp_pose = struct.unpack("!6d", data[444:492])
            tcp_speed = struct.unpack("!6d", data[492:540])
            tgt_q = struct.unpack("!6d", data[12:60])

            for i in range(6):
                row[f"Act_q{i}"] = act_q[i]
                row[f"Act_qd{i}"] = act_qd[i]
                row[f"Act_I{i}"] = act_i[i]
                row[f"Tgt_q{i}"] = tgt_q[i]

            row["Act_X"], row["Act_Y"], row["Act_Z"], row["Act_RX"], row["Act_RY"], row["Act_RZ"] = tcp_pose
            row["Act_dX"], row["Act_dY"], row["Act_dZ"], row["Act_dRX"], row["Act_dRY"], row["Act_dRZ"] = tcp_speed
            row["Robot_Mode"] = struct.unpack("!d", data[756:764])[0]
            row["Safety_Mode"] = struct.unpack("!d", data[812:820])[0]
            row["Main_Voltage"] = struct.unpack("!d", data[1004:1012])[0]
            row["Robot_Voltage"] = struct.unpack("!d", data[1012:1020])[0]
            row["Robot_Current"] = struct.unpack("!d", data[1020:1028])[0]
            return row
        except Exception:
            return None
