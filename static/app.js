// API Configuration
const LOCAL_API = "http://127.0.0.1:8791";
const SERVER_API = window.location.origin;
let selectedDevice = null;
let currentPackageName = null;
let isLocalConnected = false;

// UI Elements
const clientInfoEl = document.getElementById('clientInfo');
const deviceTableBody = document.getElementById('deviceListBody');
const connectionStatusEl = document.getElementById('connectionStatus');

async function checkLocalService() {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 1000);
        const res = await fetch(`${LOCAL_API}/devices`, { signal: controller.signal });
        clearTimeout(timeoutId);

        if (res.ok) {
            if (!isLocalConnected) {
                console.log("Connected to local service!");
                isLocalConnected = true;
                updateClientInfo(true);
                refreshDevices();
            }
            return true;
        }
    } catch (e) {
        // console.log("Local service not found", e);
    }

    if (isLocalConnected) {
        console.log("Lost connection to local service");
        isLocalConnected = false;
        updateClientInfo(false);
        refreshDevices();
    }
    return false;
}

function updateClientInfo(connected) {
    const infoDiv = document.getElementById('clientInfo');
    if (connected) {
        infoDiv.innerHTML = `
            <span style="margin-right: 15px;">作者：陈文坤</span>
            <span style="margin-right: 15px;">IP: 127.0.0.1</span>
            <span style="color: #52c41a;">● 服务已连接</span>
        `;
    } else {
        infoDiv.innerHTML = `
            <span style="margin-right: 15px;">版本: -</span>
            <span style="color: #ff4d4f;">● 服务未连接</span>
        `;
    }
}
// Toast Function
// Toast Function
function showToast(message, duration = 3000) {
    const container = document.getElementById('toastContainer') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = 'toast-message';
    toast.innerText = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

function createToastContainer() {
    const div = document.createElement('div');
    div.id = 'toastContainer';
    div.className = 'toast-container';
    document.body.appendChild(div);
    return div;
}

// Helper: Button Loading State
function setButtonLoading(btn, isLoading, loadingText = "执行中...") {
    if (isLoading) {
        btn.dataset.originalText = btn.innerHTML; // Save original HTML (including icon)
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner"></span> ${loadingText}`;
    } else {
        btn.disabled = false;
        btn.innerHTML = btn.dataset.originalText;
    }
}

async function refreshDevices() {
    const deviceTableBody = document.getElementById('deviceListBody');
    // Don't clear immediately to avoid flickering

    try {
        const res = await fetch(`${LOCAL_API}/devices`);
        if (res.ok) {
            updateClientInfo(true);
        } else {
            updateClientInfo(false);
        }

        const devices = await res.json();

        deviceTableBody.innerHTML = ''; // Clear now

        if (devices.length === 0) {
            deviceTableBody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#999;">暂无设备连接</td></tr>';
            // Do not redirect, just show message
            updateClientInfo(true); // Service is ok, just no devices
            return;
        } else {
            devices.forEach(d => {
                const tr = document.createElement('tr');
                tr.className = 'device-row';
                if (selectedDevice === d.serial) {
                    tr.classList.add('selected');
                }

                // Status Badge
                let statusHtml = '';
                if (d.state === 'device') {
                    if (d.screen_on && d.unlocked) {
                        statusHtml = '<span class="status-badge status-ok">就绪</span>';
                    } else {
                        statusHtml = '<span class="status-badge status-err">屏幕锁定/关闭</span>';
                    }
                } else {
                    statusHtml = `<span class="status-badge status-err">${d.state}</span>`;
                }
                // Platform Icon
                let platformIcon = '';
                if (d.platform === 'ios') {
                    platformIcon = '<span class="material-symbols-outlined" style="font-size: 18px; color: #555; vertical-align: middle; margin-right: 4px;">phone_iphone</span>';
                } else {
                    platformIcon = '<span class="material-symbols-outlined" style="font-size: 18px; color: #3DDC84; vertical-align: middle; margin-right: 4px;">android</span>';
                }

                tr.innerHTML = `
                    <td>${platformIcon}${d.serial}</td>
                    <td>${d.model || '-'}</td>
                    <td>${statusHtml}</td>
                    <td>
                        <button class="btn btn-primary" onclick="checkAndSelectDevice('${d.serial}', ${d.screen_on}, ${d.unlocked}, '${d.platform}')">选择</button>
                    </td>
                `;
                deviceTableBody.appendChild(tr);
            });

            // Auto-select first device if none selected or current one lost
            // Only auto-select if it's ready? User didn't specify, but let's keep it simple for now.
            // If user wants to block manual selection, auto-selection might also need check, 
            // but usually auto-select is for convenience. Let's leave auto-select as is for now 
            // or check status. Given "Not give choice", maybe auto-select should also skip bad devices.
            if (!selectedDevice || !deviceStillConnected) {
                const readyDevice = devices.find(d => d.screen_on && d.unlocked);
                if (readyDevice) {
                    selectDevice(readyDevice.serial, readyDevice.platform);
                } else if (devices.length > 0) {
                    // If no ready device, maybe don't select any? Or select first but it will be unusable?
                    // Let's just select first to show it exists, but user can't "click" to select others.
                    // Actually, if we select a locked device, the user sees it.
                    // Let's stick to: Manual click is blocked. Auto-select tries to find a good one.
                    if (devices[0].screen_on && devices[0].unlocked) {
                        selectDevice(devices[0].serial, devices[0].platform);
                    }
                }
            } else {
                // Ensure UI is synced even if already selected
                const logDeviceSpan = document.getElementById('logCurrentDevice');
                if (logDeviceSpan && selectedDevice) {
                    logDeviceSpan.textContent = `当前: ${selectedDevice}`;
                }
            }
        }

        // Refresh APKs from Server
        refreshApks();

    } catch (e) {
        console.error("Failed to fetch devices", e);
        updateClientInfo(false);
        // Do not redirect
    }
}

function checkAndSelectDevice(serial, screenOn, unlocked, platform = 'android') {
    if (!screenOn || !unlocked) {
        showToast("设备未就绪 (屏幕关闭或锁定)", 3000);
        return;
    }
    selectDevice(serial, platform);
}

let currentFileTab = 'android';
let allFiles = { android: [], ios: [] };
let selectedPlatform = 'android'; // Default

function switchFileTab(tab) {
    currentFileTab = tab;

    // Update Tab UI
    const btnAndroid = document.getElementById('tabAndroid');
    const btnIos = document.getElementById('tabIos');

    // Reset styles
    const activeStyle = "px-4 py-1.5 rounded-md text-sm font-bold transition-all";
    const inactiveStyle = "px-4 py-1.5 rounded-md text-sm font-medium text-gray-500 hover:text-gray-700 transition-all";

    if (tab === 'android') {
        btnAndroid.className = activeStyle;
        btnAndroid.style.color = "var(--primary-color)";
        btnAndroid.style.background = "white";
        btnAndroid.style.boxShadow = "0 1px 3px rgba(0,0,0,0.1)";

        btnIos.className = inactiveStyle;
        btnIos.style.color = "";
        btnIos.style.background = "";
        btnIos.style.boxShadow = "";
    } else {
        btnAndroid.className = inactiveStyle;
        btnAndroid.style.color = "";
        btnAndroid.style.background = "";
        btnAndroid.style.boxShadow = "";

        btnIos.className = activeStyle;
        btnIos.style.color = "var(--primary-color)";
        btnIos.style.background = "white";
        btnIos.style.boxShadow = "0 1px 3px rgba(0,0,0,0.1)";
    }

    renderApkList();
}

function renderApkList() {
    const listBody = document.getElementById('apkListBody');
    listBody.innerHTML = '';

    // Note: Selects are now updated by updateTestControlOptions when device is selected
    // or when files are refreshed if a device is already selected.
    if (selectedDevice) {
        updateTestControlOptions();
    }

    const files = allFiles[currentFileTab] || [];

    if (files.length === 0) {
        listBody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#999;">暂无文件</td></tr>';
        return;
    }

    files.forEach(f => {
        const tr = document.createElement('tr');
        const displayName = f.custom_name || f.filename;
        const versionInfo = `${f.version_name} (${f.version_code})`;

        tr.innerHTML = `
            <td>
                <div style="font-weight: 500;">${displayName}</div>
                <div style="font-size: 0.75rem; color: #999;">${f.filename}</div>
            </td>
            <td>
                <div style="font-size: 0.9rem;">${versionInfo}</div>
                <div style="font-size: 0.75rem; color: #999;">${f.package_name || f.bundle_id || '-'}</div>
            </td>
            <td style="font-size: 0.85rem; color: #666;">${f.upload_time}</td>
            <td style="text-align: center;">
                <button class="btn-icon delete" onclick="deleteApk('${f.filename}')" title="删除">
                    <span class="material-symbols-outlined" style="font-size: 18px;">delete</span>
                </button>
            </td>
        `;
        listBody.appendChild(tr);
    });
}

function updateTestControlOptions() {
    const oldSelect = document.getElementById('oldApkSelect');
    const newSelect = document.getElementById('newApkSelect');
    const oldLabel = document.querySelector('label[for="oldApkSelect"]');
    const newLabel = document.querySelector('label[for="newApkSelect"]');

    // Save current selection
    const oldVal = oldSelect.value;
    const newVal = newSelect.value;

    oldSelect.innerHTML = '<option value="">-- 请选择 --</option>';
    newSelect.innerHTML = '<option value="">-- 请选择 --</option>';

    let files = [];
    if (selectedPlatform === 'ios') {
        files = allFiles.ios || [];
        if (oldLabel) oldLabel.textContent = "旧版本 App (IPA)";
        if (newLabel) newLabel.textContent = "新版本 App (IPA)";
    } else {
        files = allFiles.android || [];
        if (oldLabel) oldLabel.textContent = "旧版本 APK";
        if (newLabel) newLabel.textContent = "新版本 APK";
    }

    files.forEach(f => {
        const option = document.createElement('option');
        option.value = f.filename;
        option.textContent = f.custom_name ? `${f.custom_name} (${f.version_name})` : f.filename;
        option.dataset.pkg = f.package_name || f.bundle_id;

        oldSelect.appendChild(option.cloneNode(true));
        newSelect.appendChild(option);
    });

    // Try to restore selection if valid
    // (Simple restore, might fail if switching platforms, which is desired)
    oldSelect.value = oldVal;
    newSelect.value = newVal;
}

async function refreshApks() {
    try {
        const res = await fetch(`${SERVER_API}/apks`);
        if (res.ok) {
            const data = await res.json();
            if (Array.isArray(data)) { // Old format, assume android
                allFiles.android = data;
                allFiles.ios = [];
            } else { // New format {android: [], ios: []}
                allFiles = data;
            }
            renderApkList();
        }
    } catch (e) {
        console.error("Failed to fetch APKs", e);
    }
}

async function downloadPgyer() {
    const urlInput = document.getElementById('pgyerUrl');
    const remarkInput = document.getElementById('pgyerRemark');
    const btn = document.getElementById('btnPgyerDownload');
    const progressDiv = document.getElementById('pgyerProgress');
    const progressBar = document.getElementById('pgyerProgressBar');
    const progressText = document.getElementById('pgyerProgressText');

    const url = urlInput.value.trim();

    if (!url) {
        showToast("请输入蒲公英链接");
        return;
    }

    setButtonLoading(btn, true, "请求中...");
    progressDiv.style.display = 'block';
    progressBar.style.width = '0%';
    progressText.textContent = '准备下载...';

    try {
        const res = await fetch(`${SERVER_API}/pgyer/download`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: url,
                remark: remarkInput ? remarkInput.value : ""
            })
        });

        const result = await res.json();
        if (result.status === 'started') {
            pollPgyerProgress(result.task_id);
        } else {
            showToast(`请求失败: ${result.message}`, 5000);
            setButtonLoading(btn, false);
            progressDiv.style.display = 'none';
        }
    } catch (e) {
        showToast(`请求失败: ${e.message}`, 5000);
        setButtonLoading(btn, false);
        progressDiv.style.display = 'none';
    }
}

async function pollPgyerProgress(taskId) {
    const btn = document.getElementById('btnPgyerDownload');
    const progressBar = document.getElementById('pgyerProgressBar');
    const progressText = document.getElementById('pgyerProgressText');
    const urlInput = document.getElementById('pgyerUrl');

    try {
        const res = await fetch(`${SERVER_API}/pgyer/progress/${taskId}`);
        const data = await res.json();

        if (data.percent !== undefined) {
            progressBar.style.width = `${data.percent}%`;
        }
        if (data.message) {
            progressText.textContent = data.message;
        }

        if (data.status === 'success') {
            showToast(`下载成功: ${data.filename}`, 3000);
            setButtonLoading(btn, false);
            urlInput.value = '';
            refreshApks();
            setTimeout(() => {
                document.getElementById('pgyerProgress').style.display = 'none';
            }, 3000);
        } else if (data.status === 'error') {
            showToast(`下载失败: ${data.message}`, 5000);
            setButtonLoading(btn, false);
            document.getElementById('pgyerProgress').style.display = 'none';
        } else {
            // Continue polling
            setTimeout(() => pollPgyerProgress(taskId), 1000);
        }
    } catch (e) {
        console.error("Polling error", e);
        setButtonLoading(btn, false);
        document.getElementById('pgyerProgress').style.display = 'none';
    }
}

async function uploadApk() {
    const fileInput = document.getElementById('apkFile');
    const remarkInput = document.getElementById('uploadRemark');
    const filenameInput = document.getElementById('uploadFilename');
    const statusDiv = document.getElementById('uploadStatus');

    if (fileInput.files.length === 0) {
        showToast("请选择文件");
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    if (remarkInput && remarkInput.value) {
        formData.append('remark', remarkInput.value);
    }
    if (filenameInput && filenameInput.value) {
        formData.append('custom_filename', filenameInput.value);
    }

    statusDiv.innerText = "上传中...";

    try {
        const res = await fetch(`${SERVER_API}/upload`, {
            method: 'POST',
            body: formData
        });
        const result = await res.json();

        if (result.status === 'success') {
            statusDiv.innerText = "上传成功";
            statusDiv.style.color = "green";
            fileInput.value = ''; // Clear input
            if (remarkInput) remarkInput.value = '';
            if (filenameInput) filenameInput.value = '';
            refreshApks();
            showToast("APK 上传成功");
        } else {
            statusDiv.innerText = "上传失败: " + result.message;
            statusDiv.style.color = "red";
            showToast("上传失败: " + result.message);
        }
    } catch (e) {
        statusDiv.innerText = "上传错误: " + e;
        statusDiv.style.color = "red";
        showToast("上传错误: " + e);
    }
}

async function deleteApk(filename) {
    if (!confirm(`确定要删除 ${filename} 吗？`)) return;

    try {
        const res = await fetch(`${SERVER_API}/apks/${filename}`, {
            method: 'DELETE'
        });
        const result = await res.json();
        if (result.status === 'success') {
            showToast("删除成功");
            refreshApks();
        } else {
            showToast("删除失败: " + result.message);
        }
    } catch (e) {
        showToast("删除错误: " + e);
    }
}

function selectDevice(serial, platform = 'android') {
    selectedDevice = serial;
    selectedPlatform = platform;

    const displaySerial = `${serial} (${platform === 'ios' ? 'iOS' : 'Android'})`;
    document.getElementById('currentDeviceSerial').innerText = displaySerial;

    refreshDevices(); // Re-render to highlight

    // Enable Test Card
    const testCard = document.getElementById('testControlCard');
    testCard.style.opacity = '1';
    testCard.style.pointerEvents = 'auto';

    // Reset Buttons
    document.getElementById('btnStep1').disabled = false;
    const btn2 = document.getElementById('btnStep2');
    btn2.style.display = 'inline-block'; // Always show
    btn2.disabled = true; // Initially disabled
    btn2.style.opacity = '0.5';
    btn2.style.cursor = 'not-allowed';

    // Update Options immediately
    updateTestControlOptions();
    // Also refresh APKs to ensure list is up to date
    refreshApks();
}

async function runTestStep1() {
    const deviceSerial = document.getElementById('currentDeviceSerial').innerText;
    const oldApk = document.getElementById('oldApkSelect').value;
    const newApk = document.getElementById('newApkSelect').value;

    if (!deviceSerial || deviceSerial === "未选择设备") {
        showToast("请先选择设备");
        return;
    }
    if (!oldApk || !newApk) {
        showToast("请选择 APK");
        return;
    }

    const logArea = document.getElementById('logArea');
    logArea.value = `[${new Date().toLocaleTimeString()}] 开始第一步: 安装旧版本...\n`;

    showToast("即将开始第一步：安装旧版本 APK。请确保设备屏幕已解锁。", 2000);

    const btn1 = document.getElementById('btnStep1');
    const btn2 = document.getElementById('btnStep2');

    // Set Loading
    setButtonLoading(btn1, true, "正在安装旧版本...");

    // Ensure Step 2 is disabled
    btn2.disabled = true;
    btn2.style.opacity = '0.5';
    btn2.style.cursor = 'not-allowed';

    // Construct Remote URL for APK
    const apkUrl = `${SERVER_API}/uploads/${oldApk}`;

    try {
        const res = await fetch(`${LOCAL_API}/install_old`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                device_serial: deviceSerial,
                old_apk_name: oldApk, // Still pass name for logging
                apk_url: apkUrl // Pass URL for download
            })
        });
        const result = await res.json();

        if (result.status === 'success') {
            logArea.value += `[${new Date().toLocaleTimeString()}] ✅ 旧版本安装成功\n`;
            logArea.value += `   包名: ${result.package_name}\n`;
            logArea.value += `   版本: ${result.version_name} (${result.version_code})\n`;
            logArea.value += `   请检查设备上的应用是否正常启动。\n`;

            currentPackageName = result.package_name;

            // Enable Step 2 Button
            btn2.disabled = false;
            btn2.style.opacity = '1';
            btn2.style.cursor = 'pointer';
            btn2.innerText = "继续: 覆盖安装新版本";

            showToast("第一步完成！旧版本已安装。请点击“继续”进行覆盖安装。", 3000);

        } else {
            logArea.value += `[${new Date().toLocaleTimeString()}] ❌ 失败: ${result.reason || result.message}\n`;
            showToast("安装旧版本失败：" + (result.reason || result.message));
        }
    } catch (e) {
        logArea.value += `[${new Date().toLocaleTimeString()}] ❌ 错误: ${e}\n`;
        showToast("请求错误：" + e);
    } finally {
        // Restore Button 1
        setButtonLoading(btn1, false);
    }
}

async function runTestStep2() {
    if (!currentPackageName) {
        showToast("未知包名，请先执行第一步");
        return;
    }
    const deviceSerial = document.getElementById('currentDeviceSerial').innerText;
    const newApk = document.getElementById('newApkSelect').value;
    const logArea = document.getElementById('logArea');

    logArea.value += `\n[${new Date().toLocaleTimeString()}] 开始第二步: 覆盖安装新版本...\n`;

    const btn2 = document.getElementById('btnStep2');
    setButtonLoading(btn2, true, "正在覆盖安装...");

    showToast("即将开始第二步：覆盖安装新版本 APK。", 2000);

    // Construct Remote URL for APK
    const apkUrl = `${SERVER_API}/uploads/${newApk}`;

    try {
        const res = await fetch(`${LOCAL_API}/install_new`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                device_serial: deviceSerial,
                new_apk_name: newApk,
                package_name: currentPackageName,
                apk_url: apkUrl
            })
        });
        const result = await res.json();

        if (result.status === 'success') {
            logArea.value += `[${new Date().toLocaleTimeString()}] ✅ ${result.message}\n`;
            logArea.value += `[${new Date().toLocaleTimeString()}] 🎉 测试完成!\n`;

            showToast("测试完成！覆盖安装成功，应用正在运行。", 3000);
        } else {
            logArea.value += `[${new Date().toLocaleTimeString()}] ❌ 失败: ${result.reason || result.message}\n`;
            showToast("覆盖安装失败：" + (result.reason || result.message));
        }
    } catch (e) {
        logArea.value += `[${new Date().toLocaleTimeString()}] ❌ 错误: ${e}\n`;
        showToast("请求错误：" + e);
    } finally {
        setButtonLoading(btn2, false);
    }
}

// Drag & Drop Logic
const dropZone = document.getElementById('dropZone');
const apkInput = document.getElementById('apkFile');
const uploadText = document.getElementById('uploadText');

if (dropZone) {
    // Input covers the zone, so no need for explicit click listener
    // dropZone.addEventListener('click', () => apkInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');

        if (e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            if (file.name.endsWith('.apk')) {
                apkInput.files = e.dataTransfer.files;
                handleFileSelect(apkInput);
            } else {
                showToast("请上传 .apk 文件");
            }
        }
    });
}

function handleFileSelect(input) {
    if (input.files.length > 0) {
        uploadText.innerText = `已选择: ${input.files[0].name}`;
        uploadText.style.color = 'var(--primary-color)';
        uploadText.style.fontWeight = 'bold';
    } else {
        uploadText.innerText = "点击或拖拽 APK 文件到此处";
        uploadText.style.color = 'var(--text-muted)';
        uploadText.style.fontWeight = 'normal';
    }
}

// Initial Load
function initApp() {
    console.log("App initializing...");
    refreshDevices();
    setInterval(refreshDevices, 5000);
    refreshApks();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
