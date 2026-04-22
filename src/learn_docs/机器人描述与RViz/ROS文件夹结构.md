# ROS 2 文件夹结构

## 一句话理解

ROS 2 开发时最重要的目录关系是：`src` 放源码，`build` 放编译过程产物，`install` 放真正运行时使用的文件，`log` 放构建日志。

## 先记住这张图

```text
工作空间
├── src/      # 你维护的源代码
├── build/    # 编译中间产物
├── install/  # 安装后的运行文件
└── log/      # 构建日志
```

## 1. ROS 2 系统目录

如果是通过 apt 安装 ROS 2，系统目录通常在：

```bash
/opt/ros/humble/
```

常见子目录：

```text
/opt/ros/humble/
├── bin/       # ros2、rviz2 等命令
├── lib/       # 动态库、Python 模块
├── include/   # C++ 头文件
├── share/     # launch、配置、包元信息等共享资源
└── setup.bash # 环境脚本
```

### 这些目录分别是做什么的

- `bin/`：命令行工具入口，比如 `ros2`、`rviz2`
- `lib/`：运行时需要的库文件
- `include/`：C++ 开发时引用的头文件
- `share/`：包资源、launch 文件、配置文件等
- `setup.bash`：配置环境变量

## 2. 工作空间目录

一个典型工作空间结构如下：

```text
ros2_ws/
├── src/
├── build/
├── install/
└── log/
```

### `src/`

放所有包的源代码。你真正维护的内容基本都在这里。

常见操作：

- 新建包
- `git clone` 别人的包
- 修改自己的代码

### `build/`

放编译过程中的中间文件。

特点：

- 自动生成
- 可以删除
- 删除后重新编译会重建

### `install/`

放安装后的结果文件。ROS 2 实际运行时，很多命令最终读的是这里。

例如：

- `ros2 run`
- `ros2 launch`
- `FindPackageShare(...)`

都会依赖 `install/` 中已经安装好的资源。

### `log/`

放构建和测试日志，主要用来排错。

## 3. 功能包内部常见结构

### Python 包常见结构

```text
my_python_package/
├── my_python_package/   # Python 模块目录
│   ├── __init__.py
│   ├── my_node.py
│   └── utils.py
├── launch/
├── config/
├── resource/
├── test/
├── package.xml
├── setup.py
└── setup.cfg
```

### C++ 包常见结构

```text
my_cpp_package/
├── src/
├── include/
├── launch/
├── config/
├── msg/
├── srv/
├── action/
├── package.xml
└── CMakeLists.txt
```

## 4. 最容易混淆的几个目录

### `src/` 和 `install/` 的区别

- `src/` 是源码
- `install/` 是运行时使用的安装结果

可以理解为：

```text
src/      -> 你写的东西
build/    -> 编译过程
install/  -> 最终给系统使用的东西
```

### `share/` 的作用

无论是系统目录还是包安装目录，`share/` 都很重要。

在包安装后，常见资源通常在：

```text
install/<package>/share/<package>/
```

这里会放：

- `package.xml`
- `launch/`
- `config/`
- `rviz/`
- `meshes/`
- 其他需要被运行时读取的资源

## 5. 实际开发时怎么判断文件该放哪里

### 代码文件

- Python 节点：放包名同名目录里
- C++ 源码：放 `src/`
- C++ 头文件：放 `include/<package_name>/`

### 资源文件

- launch：`launch/`
- 参数：`config/`
- RViz 配置：`rviz/`
- mesh / texture：通常放 `meshes/`、`textures/`

### 接口文件

- 消息：`msg/`
- 服务：`srv/`
- 动作：`action/`

## 6. 常见目录组合建议

### 小项目

```text
workspace/
└── src/
    ├── robot_description/
    ├── robot_bringup/
    └── robot_tools/
```

### 中型项目

```text
workspace/
└── src/
    ├── robot_driver/
    ├── robot_control/
    ├── robot_perception/
    └── robot_bringup/
```

### 大型项目

```text
workspace/
└── src/
    ├── interfaces/
    ├── core/
    ├── algorithms/
    ├── visualization/
    └── simulation/
```

## 7. 常见问题

### `build/`、`install/`、`log/` 可以删除吗

可以。

```bash
rm -rf build/ install/ log/
colcon build
```

### 只需要备份哪些目录

通常只需要备份 `src/`。

### 修改代码后为什么运行结果没变

常见原因：

- 没重新编译
- 没重新 `source install/setup.bash`
- Python 包没用 `--symlink-install`

## 8. 快速记忆

```text
src 是源头
build 是过程
install 是结果
log 是记录
```

## 9. 最后给自己的检查表

开始开发前，先问自己：

1. 我要改的是源码，还是安装后的结果？
2. 这个文件是代码、配置、还是资源？
3. 它应该被 `ros2 run` 使用，还是被 `ros2 launch` / `FindPackageShare` 使用？

只要把这三件事想清楚，目录基本就不会放错。
