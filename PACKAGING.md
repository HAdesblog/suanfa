# Windows EXE 打包说明

## 环境建议

- 操作系统：Windows 10/11 x64
- Python：3.10 / 3.11 / 3.12
- 推荐在干净虚拟环境内执行

## 为什么当前 Mac 不能直接产出 Windows EXE

- PyInstaller 不是通用交叉编译器；官方建议在目标操作系统上分别打包。
- 这意味着 macOS 上正常产物是 `.app` / macOS 可执行文件，Windows 的 `.exe` 最稳妥的构建环境仍然是 Windows。

## 推荐方案：GitHub Actions 云端 Windows 打包

项目里已经加入工作流文件：`.github/workflows/build-windows-exe.yml`

使用方式：

1. 把项目推到 GitHub 仓库
2. 打开仓库的 `Actions`
3. 运行 `Build Windows EXE`
4. 等待工作流完成后，在该次运行的 `Artifacts` 下载 `MimaGuard-windows-exe`

工作流会自动完成：

- 在 `windows-latest` 虚拟机上安装 Python 3.11
- 安装依赖
- 运行 `pytest`
- 执行 `pyinstaller --noconfirm --windowed --name MimaGuard run.py`
- 上传 `dist/MimaGuard/` 作为可下载构建产物

## 安装依赖

```bash
pip install -r requirements.txt
```

## 打包命令

```bash
pyinstaller --noconfirm --windowed --name MimaGuard run.py
```

打包成功后产物路径：

- `dist/MimaGuard/MimaGuard.exe`

## 单文件打包（可选）

```bash
pyinstaller --noconfirm --windowed --onefile --name MimaGuard run.py
```

## 验证建议

- 打开 exe 后验证两大模块可用
- 验证 AES 加解密互通
- 验证 MD5/SHA-256 解密提示正确
- 验证复制结果按钮可用
- 断网状态下执行所有功能

## 其他可选路线

- Windows 虚拟机：例如 Parallels Desktop、UTM、VMware Fusion，在虚拟机里按同样命令打包。
- 自托管 Windows Runner：如果你有一台 Windows 机器，可以把它挂成 GitHub Actions 自托管 Runner。
- Wine 路线：PyInstaller 文档提到在 GNU/Linux 下借助 Wine 可能可以面向 Windows 开发，但官方也说明“还需要更多细节”，因此不建议作为主方案。
