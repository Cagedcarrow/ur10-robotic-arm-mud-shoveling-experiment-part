import socket
import struct

class URFullMonitor:
    def __init__(self, robot_ip='10.160.9.21', port=30003):
        self.robot_ip = robot_ip
        self.port = port
        self.socket = None
        # 增加 Label 字段用于标记
        self.header = [
            'Time',
            'Act_q0', 'Act_q1', 'Act_q2', 'Act_q3', 'Act_q4', 'Act_q5',
            'Act_qd0', 'Act_qd1', 'Act_qd2', 'Act_qd3', 'Act_qd4', 'Act_qd5',
            'Act_I0', 'Act_I1', 'Act_I2', 'Act_I3', 'Act_I4', 'Act_I5',
            'Act_X', 'Act_Y', 'Act_Z', 'Act_RX', 'Act_RY', 'Act_RZ',
            'Act_dX', 'Act_dY', 'Act_dZ', 'Act_dRX', 'Act_dRY', 'Act_dRZ',
            'Tgt_q0', 'Tgt_q1', 'Tgt_q2', 'Tgt_q3', 'Tgt_q4', 'Tgt_q5',
            'Robot_Mode', 'Safety_Mode', 'Main_Voltage', 'Robot_Voltage', 'Robot_Current',
            'Label'
        ]

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(3)
            self.socket.connect((self.robot_ip, self.port))
            return True
        except Exception as e:
            print(f"Connection Error: {e}")
            return False

    def parse_packet(self, data):
        try:
            res = [struct.unpack('!d', data[4:12])[0]]        # Time
            res += list(struct.unpack('!6d', data[252:300]))  # Act_q
            res += list(struct.unpack('!6d', data[300:348]))  # Act_qd
            res += list(struct.unpack('!6d', data[348:396]))  # Act_I
            res += list(struct.unpack('!6d', data[444:492]))  # Act_TCP Pose
            res += list(struct.unpack('!6d', data[492:540]))  # Act_TCP Speed
            res += list(struct.unpack('!6d', data[12:60]))    # Tgt_q
            res.append(struct.unpack('!d', data[756:764])[0]) # Robot_Mode
            res.append(struct.unpack('!d', data[812:820])[0]) # Safety_Mode
            res.append(struct.unpack('!d', data[1004:1012])[0]) # Main_V
            res.append(struct.unpack('!d', data[1012:1020])[0]) # Robot_V
            res.append(struct.unpack('!d', data[1020:1028])[0]) # Robot_I
            return res
        except:
            return None