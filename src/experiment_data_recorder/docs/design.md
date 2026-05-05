# Design

## 接口

- `SessionManager.start_session(config) -> Path`
- `SessionManager.stop_session(normal_stop: bool) -> None`
- `RecorderConfig`：统一配置 UR/FT/RealSense 参数。

## 数据流

1. GUI 收集参数并构建 `RecorderConfig`。
2. `SessionManager` 创建统一会话目录。
3. `RealSenseAdapter` 写入四路视频与相机元数据。
4. `URFTAdapter` 写入融合 CSV。
5. 停止时写入 `session_metadata.txt`。

## 错误处理

- 任何子模块启动失败会触发统一停止并写入 `session_metadata.txt`。
- 采集中错误通过回调回传 GUI 状态区。
