#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from ur_full_monitor import URFullMonitor


def main() -> int:
    parser = argparse.ArgumentParser(description="UR10 realtime port 30003 connectivity test")
    parser.add_argument("--ip", default="10.160.9.21", help="Robot IP")
    parser.add_argument("--port", type=int, default=30003, help="Realtime data port")
    args = parser.parse_args()

    monitor = URFullMonitor(robot_ip=args.ip, port=args.port)
    print(f"[INFO] Connecting to {args.ip}:{args.port} ...")
    if not monitor.connect():
        print("[FAIL] TCP connect failed.")
        return 1

    try:
        packet = monitor.read_packet()
        if packet is None:
            print("[FAIL] Could not read one complete packet.")
            return 2

        row = monitor.parse_packet(packet)
        if row is None:
            print("[FAIL] Packet parse failed.")
            return 3

        print(f"[OK] Packet length: {len(packet)} bytes")
        print(f"Time: {row[0]:.6f}")
        print("Act_q:", [round(v, 6) for v in row[1:7]])
        print("Act_qd:", [round(v, 6) for v in row[7:13]])
        print("Act_I:", [round(v, 6) for v in row[13:19]])
        print("TCP Pose:", [round(v, 6) for v in row[19:25]])
        print("Robot_Mode:", round(row[37], 6))
        print("Safety_Mode:", round(row[38], 6))
        print("Main_Voltage:", round(row[39], 6))
        print("Robot_Voltage:", round(row[40], 6))
        print("Robot_Current:", round(row[41], 6))
        return 0
    finally:
        monitor.close()


if __name__ == "__main__":
    sys.exit(main())
