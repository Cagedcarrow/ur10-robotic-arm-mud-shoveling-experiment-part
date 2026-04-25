# robotiq_ft300_driver

Robotiq FT300 六维力/力矩传感器 ROS 2 Python 驱动（仅用于通信与数据发布验证）。

当前目标：验证 FT300 能否通过 RS485 通信并发布 `/ft300/wrench`。  
当前不实现：机械臂控制、MoveIt 配置、URDF 修改、TF 挂载。

## 1. 创建功能包（参考）

如果你要手工创建同类包，可用：

```bash
cd /root/ur10_ws/src
ros2 pkg create robotiq_ft300_driver --build-type ament_python --dependencies rclpy geometry_msgs launch launch_ros
```

本仓库已经创建好完整结构，无需重复执行。

## 2. 安装依赖 pyserial

推荐（ROS 2 Humble 常用方式）：

```bash
sudo apt update
sudo apt install -y python3-serial
```

可选（pip）：

```bash
pip install pyserial
```

## 3. 编译

```bash
cd /root/ur10_ws
colcon build --packages-select robotiq_ft300_driver
```

## 4. source 环境

```bash
cd /root/ur10_ws
source install/setup.bash
```

## 5. 启动节点

默认参数文件：`config/ft300_params.yaml`。

```bash
ros2 launch robotiq_ft300_driver ft300_sensor.launch.py
```

默认 `use_mock=true`，可先验证 ROS 2 topic。

### 切换为真机串口模式

```bash
ros2 launch robotiq_ft300_driver ft300_sensor.launch.py use_mock:=false port:=/dev/ttyUSB0 baudrate:=19200
```

## 6. 查看话题

```bash
ros2 topic echo /ft300/wrench
```

## 7. 查看串口设备

```bash
ls /dev/ttyUSB*
```

## 8. 给串口权限

```bash
sudo chmod 666 /dev/ttyUSB0
```

## 9. 参数说明

- `use_mock` (bool, 默认 `true`): 是否发布模拟六维力数据。
- `port` (string, 默认 `/dev/ttyUSB0`): 串口设备。
- `baudrate` (int, 默认 `19200`): 串口波特率（手册默认值）。
- `timeout` (double, 默认 `0.1`): 串口读超时。
- `frame_id` (string, 默认 `ft300_sensor_link`): 发布消息坐标系字符串。
- `publish_rate` (double, 默认 `100.0`): 发布频率（Hz）。
- `comm_mode` (string, 默认 `datastream`): 通信模式，`datastream` 或 `modbus`。
- `slave_id` (int, 默认 `9`): Modbus 从站 ID。
- `validate_crc` (bool, 默认 `true`): 是否校验 FT300 数据帧 CRC。

## 10. 协议实现说明（依据 FT-300 Manual 4.3）

- 启动数据流：通过 Modbus FC16 向寄存器 `410 (0x019A)` 写入 `0x0200`。
- 数据流帧：16 字节，格式为：
  - `<0x20><0x4E><LSB_data1><MSB_data1>...<LSB_data6><MSB_data6><LSB_crc><MSB_crc>`
- 单位换算：
  - `Fx,Fy,Fz = raw/100` (N)
  - `Mx,My,Mz = raw/1000` (Nm)
- 停止数据流：发送约 50 个 `0xFF`（约 0.5 s）。

## 11. 后续接入机械臂控制/力控（当前不实现）

后续可将 `/ft300/wrench` 接入：

1. 机械臂末端接触检测与阈值触发逻辑。
2. 基于力反馈的阻抗/顺应控制器输入。
3. MoveIt 规划中的执行中断条件或安全监测模块。

本包当前仅负责“传感器通信 + ROS 2 数据发布”。
