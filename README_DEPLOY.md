# 部署与安装指南

本指南介绍如何将 APK 兼容性测试平台作为 Docker 服务部署，或作为 Python 包安装。

## 1. Docker 部署 (服务端)

适用于在服务器上部署，提供 Web 界面和 APK 管理功能。
注意：Docker 容器内默认无法直接访问宿主机的 USB 设备。若需连接设备，建议使用远程 ADB 或以特权模式运行。

### 构建镜像

在项目根目录下运行：

```bash
docker build -t appinstalltest .
```

### 运行容器

```bash
docker run -d -p 8791:8791 --restart always --name appinstalltest appinstalltest
```

访问地址：`http://localhost:8791`

若需挂载宿主机 USB 设备（Linux）：
```bash
docker run -d -p 8791:8791 --restart always --privileged -v /dev/bus/usb:/dev/bus/usb --name appinstalltest appinstalltest
```

---

## 2. PyPI 安装 (客户端/本地工具)

适用于在本地电脑上安装，直接控制连接的 USB 设备。

### 打包

```bash
python setup.py sdist bdist_wheel
```

### 安装

生成的包位于 `dist/` 目录下，可通过 pip 安装：

```bash
pip install dist/appinstalltest-0.1.0-py3-none-any.whl
```

### 运行

安装完成后，在终端直接运行以下命令启动服务：

```bash
appinstalltest
```

服务启动后，浏览器访问 `http://localhost:8791` 即可使用。

---

## 3. 发布到 PyPI

如果您想将包发布到 PyPI 供他人下载，请按以下步骤操作：

### 准备工作

1.  注册 [PyPI](https://pypi.org/) 账号。
2.  安装上传工具 `twine`：
    ```bash
    pip install twine
    ```

### 上传

在项目根目录下运行：

```bash
twine upload dist/*
```

系统会提示输入 PyPI 的用户名和密码（或 API Token）。上传成功后，其他人即可通过 `pip install appinstalltest` 安装您的工具。

