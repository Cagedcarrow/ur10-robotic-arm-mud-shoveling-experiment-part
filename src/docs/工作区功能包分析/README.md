# 工作区功能包分析

## 这个专题解决什么问题

这个专题专门回答一个很实际的问题：

当你隔了一段时间再回到 `/root/ur10_ws/src` 这个工作区时，很容易忘记：

- 某个包到底是干什么的
- 它是主线包还是历史包
- 它应该在什么时候改
- 它和 `my_robot`、原始 `ur10`、`ur10_with_shovel` 之间是什么关系

这组文档的目的，就是把当前工作区里所有 ROS 2 功能包整理成一套“包职责地图”。

## 当前分析范围

本专题只分析当前工作区中的 ROS 2 功能包，不分析下面这些目录：

- `build/`
- `install/`
- `log/`
- `docs/`
- `learn_docs/`

当前确认的功能包共有 9 个：

- `my_robot`
- `my_robot_moveit_config`
- `ur10_description`
- `ur10_examples`
- `ur10_examples_py`
- `ur10_moveit_config`
- `ur10_perception`
- `ur10_simulation_bringup`
- `ur10_with_shovel`

## 阅读建议

推荐按这个顺序阅读：

1. `00_总览.md`
2. `01_功能包速查表.md`
3. 如果你当前主要用龙门架整机，优先看：
   - `02_my_robot_包分析.md`
   - `03_my_robot_moveit_config_包分析.md`
   - `07_ur10_perception_包分析.md`
   - `08_ur10_examples_与_ur10_examples_py_包分析.md`
4. 如果你想理解工程旧主线，再看：
   - `04_ur10_description_包分析.md`
   - `05_ur10_moveit_config_包分析.md`
   - `06_ur10_simulation_bringup_包分析.md`
5. 如果你想回顾铲斗专项路线，再看：
   - `09_ur10_with_shovel_包分析.md`
6. 最后看：
   - `10_应该从哪里开始看_修改哪一层.md`

## 这套文档怎么读最省时间

如果你只是临时忘了某个包是干什么的，最快的方法是：

1. 先看 `01_功能包速查表.md`
2. 再跳到那个包对应的单篇文档

如果你已经连“整个工程分成几条线”都记不清了，那就先看 `00_总览.md`。

## 一句话总结

当前这套工程不是一条单线，而是 3 条路线叠加出来的：

- 原始 UR10 仿真主线
- UR10 + 铲斗专项主线
- 当前最常用的 `my_robot` 龙门架整机主线

所以“忘记包用途”其实很正常，因为不同包来自不同阶段、解决的是不同层次的问题。
