# 使用说明（当前流程）

## 1. 安装依赖
```bash
cd ~/ur10_ws/src/ur10_ft300_monitor
pip install -r requirements.txt
```

## 2. 采集数据
```bash
python3 run_gui.py
```
- 填 UR/FT300 参数
- 点击 `开始采集`
- 需要时按 `实验标记 (Space)`
- 点击 `停止采集`

采集结果：
- `data/YYYYMMDD_HHMMSS/ur10_ft300_realtime_data.csv`
- `data/YYYYMMDD_HHMMSS/metadata.txt`

## 3. 配置 DeepSeek
编辑 `config/llm_config.yaml`：
- `api_key`: 你的 DeepSeek key
- `model`: 建议 `deepseek-v4-pro` 或你可用的模型
- `base_url`: 默认 `https://api.deepseek.com`

## 4. 分析数据（唯一入口）
```bash
python3 analysis/run_analysis_gui.py
```
- 点击 `读取数据文件夹`
- 点击 `测试DeepSeek连接`（建议）
- 点击 `执行分析`

输出目录：
- `results/<数据文件夹名>_analysis_result/`

## 5. API快速测试（可选）
```bash
python3 config/test_deepseek_api.py
```
