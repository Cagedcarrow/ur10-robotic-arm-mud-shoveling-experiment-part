# Gazebo 为什么显示不出来

## 这篇文档解决什么问题

很多 ROS 2 新手第一次遇到 Gazebo 不显示模型时，脑子里会默认觉得：

- 是不是 STL 坏了。
- 是不是显卡有问题。
- 是不是 Gazebo 太卡。

这些猜法不一定错，但更常见的情况是：显示链路中的某一环断了。

这篇文档的目标，就是用新手能理解的方式，把 Gazebo 显示链路讲清楚。

## 先理解一条最重要的链路

这次项目里，Gazebo 能不能把机械臂显示出来，核心链路可以粗略理解为：

```text
xacro -> URDF -> robot_description -> spawn_entity -> gzserver -> SDF/mesh/world/plugin
```

下面按顺序解释。

### 1. xacro

`xacro` 可以理解成“带变量和宏的机器人描述模板”。

你真正维护的通常不是一份最终 URDF，而是一份 `.urdf.xacro` 文件。启动时，它会先被展开成纯 URDF。

### 2. URDF

URDF 可以理解成“机器人的结构说明书”。

它描述：

- 有哪些 link
- 有哪些 joint
- 它们怎么连接
- mesh 文件在哪里
- 惯量和碰撞体是什么

### 3. robot_description

`robot_description` 是 ROS 里很常见的一个参数名。

你可以把它理解成：

- “当前机器人模型的文本内容”

很多节点都会去读它，比如：

- `robot_state_publisher`
- `gazebo_ros2_control`
- MoveIt

### 4. spawn_entity

`spawn_entity.py` 是把机器人“真的放进 Gazebo 里”的那个节点。

它做的事情大致是：

1. 从 `robot_description` 里拿模型文本
2. 调 Gazebo 的 `/spawn_entity` 服务
3. 把模型送进仿真世界

### 5. gzserver

`gzserver` 是 Gazebo 的核心仿真进程。

真正负责：

- 加载 world
- 生成模型
- 解析 mesh
- 加载插件
- 跑物理仿真

如果 `gzserver` 这一层有问题，前面 `xacro` 和 `spawn_entity` 再正常，也会出现“不显示”或“显示不完整”。

## 任一环节出错，会表现成什么

### xacro 出错

常见表现：

- 启动命令直接报错
- `robot_description` 都生成不出来

典型判断：

- 机器人根本还没到 Gazebo 这一步

### URDF 结构或命名出错

常见表现：

- `robot_state_publisher` 输出异常
- Gazebo 在解析模型时出现奇怪报错
- 某些 link 或 collision 处理失败

这次的“中文 link 名”就属于这一层。

### spawn_entity 出错

常见表现：

- `/spawn_entity` 调用失败
- Gazebo 世界里根本没有机器人实体

### gzserver 解析 mesh / world / plugin 出错

常见表现：

- 机器人只显示一部分
- 机器人看不见
- Gazebo 启动很慢
- 控制器插件不起

这次的大头问题，基本都发生在这一层。

## 这次最关键的 3 个显示问题

## 1. 中文 link 名触发 Gazebo Classic UTF-8 问题

这次模型里最可疑、最终也被证实有问题的名字是 `铲子`。

Gazebo 日志里反复出现：

```text
String field 'gazebo.msgs.Visual.name' contains invalid UTF-8 data
String field 'gazebo.msgs.Collision.name' contains invalid UTF-8 data
```

这说明 Gazebo Classic 在处理模型内部名字时出了问题。

注意，这里报错位置虽然提到了 `Visual.name` 和 `Collision.name`，但根因不一定是你显式写了 `<visual name="...">`，也可能是 Gazebo 内部在生成名称时受到了 link 名影响。

### 为什么改成 `shovel_link` 后就好了

因为 ASCII 命名对 Gazebo Classic 更稳。

也就是说，问题不在“中文一定不能在 ROS 里出现”，而在于：

- 某些 ROS 工具能接受中文
- 但 Gazebo Classic 这一段链路不稳定

所以这次最稳妥的做法，就是把真正要进入 Gazebo 的实体命名统一成 ASCII。

## 2. 铲斗 mesh URI 解析失败

后来又抓到一个关键日志：

```text
Failed to find mesh file [model://my_robot/meshes/base_link.STL]
```

这个问题和 UTF-8 不是同一个问题。

它说明的是：

- Gazebo 在尝试加载铲斗 mesh
- 但它拿到的 URI 形式变成了 `model://my_robot/...`
- 这个路径在当前环境下没被正确解析到真实文件

### 为什么这会影响显示

因为 visual mesh 本来就是“给你看的外形”。

如果 mesh 找不到，就可能出现：

- 铲斗不显示
- 某个 link 没外形
- 甚至整机加载异常

### 为什么最后改成 `file://...`

因为对于这个具体铲斗 mesh，`file://$(find my_robot)/meshes/base_link.STL` 这种形式在当前工作区和安装结构下更稳定。

它的好处是：

- 展开后就是明确的绝对文件路径
- Gazebo 不需要再猜包路径或模型路径

## 3. world 依赖模型数据库导致启动阻塞

Gazebo 世界文件 `gantry_only.world` 最开始用了：

```xml
<include>
  <uri>model://ground_plane</uri>
</include>
<include>
  <uri>model://sun</uri>
</include>
```

这本身不是错写法，但在某些环境下，Gazebo 会去做额外的模型数据库更新或查询。

这次日志里就出现过：

```text
Waiting for model database update to complete...
```

### 为什么这会让人误判

因为从表面看，你只会觉得：

- Gazebo 很慢
- 模型怎么半天不出来

但真正卡住的不是机器人本体，而是 world 自己还在等外部模型相关步骤。

### 这次为什么把地面和光源内联进 world

因为这能减少外部依赖，让 world 更“自给自足”。

好处是：

- Gazebo 启动更直接
- 少一层模型数据库等待
- 更适合离线或不稳定环境

## 对新手最重要的一个思维方式

Gazebo 不显示模型时，不要只问：

- “哪一个 STL 坏了？”

而要先问：

1. `xacro` 有没有正常展开？
2. `robot_description` 有没有生成？
3. `spawn_entity` 有没有成功？
4. `gzserver` 有没有真的把模型吃进去？
5. mesh URI 对 Gazebo 是否稳定？
6. world 本身有没有把启动拖住？

只要你按这条链去想，排障会清晰很多。
