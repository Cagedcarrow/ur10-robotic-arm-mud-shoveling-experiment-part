# 依赖与 setup.py

## 一句话理解

- 依赖声明回答的是：这个包运行或构建时需要哪些外部东西。
- `setup.py` 回答的是：我这个 Python 包应该怎样被安装、暴露哪些命令、带上哪些资源文件。

## 1. 什么是依赖

依赖就是：你的代码要用到别人已经写好的功能。

例如：

```python
import rclpy
from std_msgs.msg import String
import numpy as np
```

这三行分别说明你依赖：

- `rclpy`
- `std_msgs`
- `numpy`

如果这些依赖没装好，你的代码就跑不起来。

## 2. ROS 2 里常见依赖类型

### `buildtool_depend`

构建工具依赖。

常见例子：

- `ament_cmake`
- `ament_python`

### `build_depend`

编译时依赖，常见于 C++ 包或接口包。

### `exec_depend`

运行时依赖，最常见。

Python 包里最常写的是它。

### `test_depend`

测试时需要的依赖。

## 3. package.xml 里怎么写依赖

### Python 包最小示例

```xml
<package format="3">
  <name>my_python_package</name>
  <version>0.0.1</version>
  <description>example package</description>
  <maintainer email="user@example.com">User</maintainer>
  <license>Apache-2.0</license>

  <buildtool_depend>ament_python</buildtool_depend>

  <exec_depend>rclpy</exec_depend>
  <exec_depend>std_msgs</exec_depend>

  <export>
    <build_type>ament_python</build_type>
  </export>
</package>
```

### 怎么判断该不该加依赖

直接看代码：

- `import rclpy` -> `rclpy`
- `from std_msgs.msg import String` -> `std_msgs`
- `import cv2` -> `python3-opencv`
- `import numpy` -> `python3-numpy`

## 4. setup.py 是干什么的

`setup.py` 主要做三件事：

1. 安装你的 Python 模块
2. 安装 launch / config / rviz 等资源文件
3. 创建 `ros2 run` 能调用的命令入口

## 5. setup.py 最重要的两个部分

### `data_files`

决定哪些非代码文件会被安装到 `share/<package_name>/`。

例如：

```python
data_files=[
    ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
    ('share/' + package_name + '/launch', ['launch/demo.launch.py']),
    ('share/' + package_name + '/config', ['config/params.yaml']),
]
```

### `entry_points`

决定 `ros2 run <package> <executable>` 的 `<executable>` 是什么。

```python
entry_points={
    'console_scripts': [
        'talker = my_package.publisher_node:main',
    ],
}
```

这表示：

```bash
ros2 run my_package talker
```

实际会去执行：

```python
my_package.publisher_node.main()
```

## 6. package.xml 和 setup.py 的区别

| 项目 | package.xml | setup.py |
| --- | --- | --- |
| 回答的问题 | 我需要什么依赖 | 我自己怎么安装 |
| 关注对象 | 外部包 | 你自己的包和资源 |
| 常见内容 | `exec_depend`、`buildtool_depend` | `data_files`、`entry_points` |
| 主要影响 | 环境是否齐全 | 节点、launch、配置能否被找到 |

可以记成：

- `package.xml` 管“我缺什么”
- `setup.py` 管“我怎么装”

## 7. 一个最小可运行示例

### package.xml

```xml
<buildtool_depend>ament_python</buildtool_depend>
<exec_depend>rclpy</exec_depend>
<exec_depend>std_msgs</exec_depend>
```

### setup.py

```python
entry_points={
    'console_scripts': [
        'my_node = my_pkg.my_node:main',
    ],
}
```

### 节点文件

```python
def main():
    print('hello ros2')
```

然后可以运行：

```bash
ros2 run my_pkg my_node
```

## 8. 常见错误

### `ImportError`

常见原因：

- `package.xml` 没声明运行依赖
- 依赖没安装
- 没重新 source 环境

### `ros2 run` 找不到节点命令

常见原因：

- `setup.py` 里没写 `entry_points`
- 命令名写错
- 函数路径写错

### `ros2 launch` 找不到 launch 文件

常见原因：

- `setup.py` 里没把 `launch/` 安装进去
- 编译后没重新 source

## 9. 常用命令

### 安装依赖

```bash
rosdep install --from-paths src --ignore-src -r -y
```

### 重新编译并使用符号链接

```bash
colcon build --packages-select my_package --symlink-install
source install/setup.bash
```

## 10. 快速记忆

```text
依赖写在 package.xml
安装规则写在 setup.py
缺依赖，程序跑不起来
没入口，ros2 run 找不到
没 data_files，launch/config 找不到
```
