#!/usr/bin/env python3
"""ROS 2 node for Robotiq FT300 force/torque sensor data publishing.

This node focuses only on FT300 communication and publishing wrench data.
It does not contain any robot arm control logic.
"""

import math
import struct
from typing import Optional, Tuple

import rclpy
from geometry_msgs.msg import WrenchStamped
from rclpy.node import Node

try:
    import serial
    from serial import SerialException
except ImportError as exc:
    raise ImportError(
        "pyserial is required for robotiq_ft300_driver. Install via: sudo apt install python3-serial"
    ) from exc


FT300_FRAME_SIZE = 16
FT300_HEADER = b"\x20\x4E"


def modbus_crc16(data: bytes) -> int:
    """Compute standard Modbus RTU CRC16 for bytes."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def build_fc16_write_single_register_request(slave_id: int, address: int, value: int) -> bytes:
    """Build Modbus FC16 request for writing one register."""
    # Request format:
    # [slave_id][0x10][addr_hi][addr_lo][0x00][0x01][0x02][val_hi][val_lo][crc_lo][crc_hi]
    payload = bytes(
        [
            slave_id & 0xFF,
            0x10,
            (address >> 8) & 0xFF,
            address & 0xFF,
            0x00,
            0x01,
            0x02,
            (value >> 8) & 0xFF,
            value & 0xFF,
        ]
    )
    crc = modbus_crc16(payload)
    return payload + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def parse_ft300_frame(frame: bytes, validate_crc: bool = True) -> Optional[Tuple[float, float, float, float, float, float]]:
    """Parse one FT300 Data Stream frame into wrench values.

    FT-300 Manual 4.3.2 DataStream format:
    <0x20><0x4e><LSB_data1><MSB_data1>...<LSB_data6><MSB_data6><LSB_crc><MSB_crc>

    data1..data6 are signed int16 values with scaling:
      Fx,Fy,Fz = raw / 100   (N)
      Mx,My,Mz = raw / 1000  (Nm)

    TODO: 如果你的传感器固件版本通信细节与手册不一致，
    这里需要根据 Robotiq FT300 官方通信协议填写/调整数据帧解析逻辑。
    """
    if len(frame) != FT300_FRAME_SIZE:
        return None

    if frame[:2] != FT300_HEADER:
        return None

    if validate_crc:
        expected_crc = frame[-2] | (frame[-1] << 8)
        computed_crc = modbus_crc16(frame[:-2])
        if expected_crc != computed_crc:
            return None

    raw_values = []
    for i in range(6):
        offset = 2 + i * 2
        # LSB first, then MSB (little-endian data payload)
        raw = struct.unpack_from("<h", frame, offset)[0]
        raw_values.append(raw)

    fx = raw_values[0] / 100.0
    fy = raw_values[1] / 100.0
    fz = raw_values[2] / 100.0
    tx = raw_values[3] / 1000.0
    ty = raw_values[4] / 1000.0
    tz = raw_values[5] / 1000.0

    return (fx, fy, fz, tx, ty, tz)


class FT300SensorNode(Node):
    """Node that reads FT300 serial data and publishes WrenchStamped."""

    def __init__(self) -> None:
        super().__init__("ft300_sensor_node")

        self.declare_parameter("use_mock", True)
        self.declare_parameter("port", "/dev/ttyUSB0")
        self.declare_parameter("baudrate", 19200)
        self.declare_parameter("timeout", 0.1)
        self.declare_parameter("frame_id", "ft300_sensor_link")
        self.declare_parameter("publish_rate", 100.0)
        self.declare_parameter("comm_mode", "datastream")
        self.declare_parameter("slave_id", 9)
        self.declare_parameter("validate_crc", True)

        self.use_mock = bool(self.get_parameter("use_mock").value)
        self.port = str(self.get_parameter("port").value)
        self.baudrate = int(self.get_parameter("baudrate").value)
        self.timeout = float(self.get_parameter("timeout").value)
        self.frame_id = str(self.get_parameter("frame_id").value)
        self.publish_rate = float(self.get_parameter("publish_rate").value)
        self.comm_mode = str(self.get_parameter("comm_mode").value).strip().lower()
        self.slave_id = int(self.get_parameter("slave_id").value)
        self.validate_crc = bool(self.get_parameter("validate_crc").value)

        if self.publish_rate <= 0.0:
            self.get_logger().warn("publish_rate <= 0.0, fallback to 100.0 Hz")
            self.publish_rate = 100.0

        if self.comm_mode not in ("datastream", "modbus"):
            self.get_logger().warn(
                f"Unsupported comm_mode '{self.comm_mode}', fallback to 'datastream'"
            )
            self.comm_mode = "datastream"

        self.publisher_ = self.create_publisher(WrenchStamped, "/ft300/wrench", 50)

        self.serial_conn: Optional[serial.Serial] = None
        self.byte_buffer = bytearray()
        self.mock_t = 0.0
        self.read_fail_count = 0

        if self.use_mock:
            self.get_logger().info("FT300 running in MOCK mode. Publishing simulated wrench data.")
        else:
            self.init_serial()

        timer_period = 1.0 / self.publish_rate
        self.timer = self.create_timer(timer_period, self.timer_callback)

    def init_serial(self) -> None:
        """Initialize serial port for FT300 communication."""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
            )

            self.byte_buffer.clear()
            self.get_logger().info(
                f"Opened serial port {self.port} @ {self.baudrate} bps, timeout={self.timeout}s"
            )

            if self.comm_mode == "datastream":
                self.start_datastream()
            else:
                self.get_logger().info(
                    "comm_mode='modbus': currently read path still uses frame parser when stream is available."
                )

        except SerialException as exc:
            self.serial_conn = None
            self.get_logger().error(f"Failed to open serial port {self.port}: {exc}")

    def start_datastream(self) -> None:
        """Start FT300 data stream by Modbus FC16 write to register 410 with value 0x0200."""
        if self.serial_conn is None:
            return

        request = build_fc16_write_single_register_request(
            slave_id=self.slave_id,
            address=0x019A,  # register 410
            value=0x0200,
        )

        try:
            self.serial_conn.reset_input_buffer()
            self.serial_conn.write(request)
            self.serial_conn.flush()

            # Expected FC16 response length is 8 bytes. We do not hard-fail if absent.
            response = self.serial_conn.read(8)
            if len(response) == 8:
                self.get_logger().info("FT300 datastream start command sent (FC16 reg410=0x0200).")
            else:
                self.get_logger().warn(
                    "Datastream start command sent, but FC16 response not fully received."
                )

        except SerialException as exc:
            self.get_logger().error(f"Failed to send datastream start command: {exc}")

    def stop_datastream(self) -> None:
        """Stop FT300 data stream by sending 0xFF sequence for about 0.5s (~50 bytes)."""
        if self.serial_conn is None:
            return
        try:
            self.serial_conn.write(b"\xFF" * 50)
            self.serial_conn.flush()
            self.get_logger().info("Sent 0xFF sequence to stop FT300 datastream.")
        except SerialException as exc:
            self.get_logger().warn(f"Failed to send datastream stop sequence: {exc}")

    def read_raw_frame(self) -> Optional[bytes]:
        """Read and synchronize one FT300 16-byte frame from serial stream."""
        if self.serial_conn is None:
            return None

        try:
            incoming = self.serial_conn.read(64)
            if incoming:
                self.byte_buffer.extend(incoming)

            # Keep buffer bounded
            if len(self.byte_buffer) > 4096:
                self.byte_buffer = self.byte_buffer[-256:]

            # Search for frame header and parse a complete 16-byte frame
            while len(self.byte_buffer) >= FT300_FRAME_SIZE:
                idx = self.byte_buffer.find(FT300_HEADER)
                if idx < 0:
                    # Keep only trailing byte if it might be a partial header
                    self.byte_buffer = self.byte_buffer[-1:]
                    return None

                if idx > 0:
                    del self.byte_buffer[:idx]

                if len(self.byte_buffer) < FT300_FRAME_SIZE:
                    return None

                frame = bytes(self.byte_buffer[:FT300_FRAME_SIZE])
                del self.byte_buffer[:FT300_FRAME_SIZE]
                return frame

            return None

        except SerialException as exc:
            self.get_logger().error(f"Serial read error: {exc}")
            return None

    def publish_wrench(self, wrench_values: Tuple[float, float, float, float, float, float]) -> None:
        """Publish parsed wrench data as geometry_msgs/WrenchStamped."""
        fx, fy, fz, tx, ty, tz = wrench_values

        msg = WrenchStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id

        msg.wrench.force.x = fx
        msg.wrench.force.y = fy
        msg.wrench.force.z = fz
        msg.wrench.torque.x = tx
        msg.wrench.torque.y = ty
        msg.wrench.torque.z = tz

        self.publisher_.publish(msg)

    def generate_mock_wrench(self) -> Tuple[float, float, float, float, float, float]:
        """Generate deterministic mock wrench data for topic validation."""
        self.mock_t += 1.0 / self.publish_rate

        fx = 5.0 * math.sin(2.0 * math.pi * 0.5 * self.mock_t)
        fy = 3.0 * math.cos(2.0 * math.pi * 0.4 * self.mock_t)
        fz = 10.0 + 0.8 * math.sin(2.0 * math.pi * 0.2 * self.mock_t)

        tx = 0.08 * math.sin(2.0 * math.pi * 0.3 * self.mock_t)
        ty = 0.05 * math.cos(2.0 * math.pi * 0.25 * self.mock_t)
        tz = 0.03 * math.sin(2.0 * math.pi * 0.6 * self.mock_t)

        return (fx, fy, fz, tx, ty, tz)

    def timer_callback(self) -> None:
        """Periodic callback to publish mock or sensor data."""
        if self.use_mock:
            self.publish_wrench(self.generate_mock_wrench())
            return

        if self.serial_conn is None:
            # Attempt reconnect without blocking node shutdown
            self.init_serial()
            return

        frame = self.read_raw_frame()
        if frame is None:
            return

        parsed = parse_ft300_frame(frame, validate_crc=self.validate_crc)
        if parsed is None:
            self.read_fail_count += 1
            if self.read_fail_count % 50 == 1:
                self.get_logger().warn(
                    "Failed to parse FT300 frame (header/length/CRC check). Continuing..."
                )
            return

        self.read_fail_count = 0
        self.publish_wrench(parsed)

    def destroy_node(self) -> bool:
        """Ensure serial resources are released when node is destroyed."""
        try:
            if not self.use_mock and self.serial_conn is not None:
                if self.comm_mode == "datastream":
                    self.stop_datastream()
                if self.serial_conn.is_open:
                    self.serial_conn.close()
                    self.get_logger().info("Closed FT300 serial connection.")
        except Exception as exc:  # pylint: disable=broad-except
            self.get_logger().warn(f"Exception during serial shutdown: {exc}")
        finally:
            self.serial_conn = None

        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = FT300SensorNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
