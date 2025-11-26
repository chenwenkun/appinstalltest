# APK 兼容性测试平台 (APK Compatibility Test Platform)

这是一个基于 Web 的 Android APK 兼容性测试工具，支持批量设备管理、APK 安装测试（安装旧版本 -> 覆盖安装新版本）、以及实时日志查看。

它由两部分组成：
1.  **服务端 (Web 前端)**: 静态网页，可以部署在任何 Web 服务器上。
2.  **客户端 (本地服务)**: 运行在测试人员本地的 Python 服务，负责连接 Android 设备和执行 ADB 命令。

---

## 🚀 部署指南 (Deployment Guide)

### 1. 客户端部署 (Client / Local Service)

客户端是必须运行的，它负责与 USB 连接的 Android 设备进行通信。

**环境要求:**
- Python 3.8+
- ADB (Android Debug Bridge) 已配置环境变量

**安装步骤:**

1.  **克隆或下载本项目代码**
2.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **启动服务**:
    ```bash
    python main.py
    ```
    服务默认运行在 `http://127.0.0.1:8791`。

**使用方式:**
启动服务后，你可以直接访问 `http://127.0.0.1:8791` 使用完整功能。

---

### 2. 服务端部署 (Server / Web Host)

如果你希望将网页部署到公网（例如公司内部服务器、GitHub Pages、Vercel 等），让大家通过统一的网址访问，可以按照以下步骤操作。

**原理:**
服务端只需要托管 `static` 目录下的静态文件。网页加载后，会自动尝试连接访问者本地的 `http://127.0.0.1:8791` 服务。

**部署步骤:**

1.  **准备文件**:
    提取项目中的 `static` 文件夹。该文件夹应包含：
    -   `index.html` (入口/引导页)
    -   `dashboard.html` (主控制台)
    -   `app.js` (逻辑代码)
    -   `favicon.png`
    -   `style.css` (如果有独立 CSS)

2.  **上传至 Web 服务器**:
    将 `static` 文件夹的内容上传到你的 Nginx, Apache, 或静态托管服务（如 GitHub Pages）。

3.  **配置 (可选)**:
    确保 Web 服务器能够正确服务 `.html`, `.js`, `.css` 文件。

**访问流程:**
1.  用户访问你的公网地址（例如 `http://your-internal-tool.com`）。
2.  页面显示“安装指南”。
3.  页面自动检测用户本地是否启动了 **客户端服务** (`127.0.0.1:8791`)。
    -   ✅ **已启动**: 自动跳转到控制台，开始测试。
    -   ❌ **未启动**: 提示用户运行 `python main.py`。

---

## 🛠 开发与维护

-   **后端 (`main.py`)**: 基于 FastAPI，处理 `/devices`, `/upload`, `/install` 等 API 请求。
-   **前端 (`static/`)**: 原生 HTML/JS，无构建步骤，修改即生效。

### 目录结构
```
.
├── main.py                 # Python 后端入口
├── device_manager.py       # 设备管理逻辑
├── apk_manager.py          # APK 管理逻辑
├── test_runner.py          # 测试执行逻辑
├── requirements.txt        # Python 依赖
└── static/                 # 前端静态资源
    ├── index.html          # 引导页
    ├── dashboard.html      # 主页面
    └── app.js              # 前端逻辑
```
