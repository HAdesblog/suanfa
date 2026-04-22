# Mima Guard

离线 Windows 密码工具，支持密码制作（加/解密、摘要）与密码强度检测。

## 功能范围

- 密码制作模块
  - 支持 `Caesar`、`Rail Fence`、`MD5`、`SHA-256`、`AES-GCM`
  - 支持加密/解密切换，MD5/SHA-256 在解密时给出不可逆提示
  - 结果一键复制
- 密码强度检测模块
  - 长度检测
  - 字符类型统计（大写/小写/数字/符号）
  - 弱密码规则检测（连续字符、重复字符、重复片段）
  - 常见密码字典匹配（内置 Top 列表）
  - 综合评分（0-100）+ 简单建议
- 展示辅助
  - 每种算法附带用途和安全性说明

## 本地运行

1. 安装 Python 3.10+（建议 3.11）
2. 安装依赖

```bash
pip install -r requirements.txt
```

3. 启动应用

```bash
python run.py
```

## 目录结构

```text
app/
  crypto_algorithms.py
  strength.py
  ui/main_window.py
tests/
  test_crypto.py
  test_strength.py
scripts/
  generate_demo_video.py
  generate_screenshots.py
docs/screenshots/
docs/videos/
```

## 运行测试

```bash
python -m pytest -q
```

## 生成功能截图

```bash
python scripts/generate_screenshots.py
```

## 生成演示视频

```bash
python scripts/generate_demo_video.py
```

运行后会生成标准版视频：`docs/videos/mima_demo.mp4`

生成更有真人操作感的慢节奏版本：

```bash
python scripts/generate_demo_video.py --style human
```

运行后会生成真人版视频：`docs/videos/mima_demo_human.mp4`

## 运行兼容性检查

```bash
python scripts/compatibility_check.py
```

运行后会生成报告：`docs/compatibility_runtime_report.md`

## 打包 EXE

详见 [`PACKAGING.md`](PACKAGING.md)

如果当前机器是 macOS，也可以把项目推到 GitHub 后使用仓库里的 Windows 工作流：
`.github/workflows/build-windows-exe.yml`
