import { renderProfileCorner } from '../components/ProfileCorner.js';
import { renderProfileModal } from '../components/ProfileModal.js';
import { renderPreviewModal } from '../components/PreviewModal.js';
import { renderResultModal } from '../components/ResultModal.js';
import { renderCommandInput } from '../components/CommandInput.js';
import { renderFileList } from '../components/FileList.js';
import { uploadFiles, executeCommand } from '../api/index.js';
import { escapeHtml, toggleFullscreen, formatFileSize } from '../utils/helpers.js';

// 全局状态
let fileArray = [];
let currentAvatar = 'data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'40\' height=\'40\' viewBox=\'0 0 24 24\' fill=\'%2394a3b8\'%3E%3Cpath d=\'M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z\'/%3E%3C/svg%3E';
let currentName = '旅行者';

// DOM元素引用 (将在init中填充)
let elements = {};

// 允许的扩展名
const allowedExtensions = ['.txt', '.md', '.doc', '.docx', '.xls', '.xlsx'];

// ---------- 辅助函数 ----------
function setStatus(text, type = 'info') {
    const statusMsg = document.getElementById('statusMsg');
    statusMsg.textContent = text;
    statusMsg.classList.remove('error', 'success');
    if (type === 'error') statusMsg.classList.add('error');
    else if (type === 'success') statusMsg.classList.add('success');
    setTimeout(() => {
        if (statusMsg.textContent === text) {
            statusMsg.textContent = '就绪，可添加文件';
            statusMsg.classList.remove('error', 'success');
        }
    }, 3000);
}

function isValidFileType(file) {
    const fileName = file.name || '';
    const dotIndex = fileName.lastIndexOf('.');
    if (dotIndex === -1) return false;
    const ext = fileName.slice(dotIndex).toLowerCase();
    return allowedExtensions.includes(ext);
}

function isDuplicate(file) {
    return fileArray.some(item =>
        item.file.name === file.name &&
        item.file.size === file.size &&
        item.file.lastModified === file.lastModified
    );
}

function addFiles(newFileList) {
    if (!newFileList || newFileList.length === 0) return;
    const files = Array.from(newFileList);
    const invalidFiles = [];
    let addedCount = 0;

    files.forEach(file => {
        if (!isValidFileType(file)) {
            invalidFiles.push(file.name);
            return;
        }
        if (isDuplicate(file)) return;
        fileArray.push({
            file: file,
            id: Date.now() + Math.random() + addedCount
        });
        addedCount++;
    });

    updateFileList();
    if (addedCount > 0) setStatus(`✅ 成功添加 ${addedCount} 个文件`, 'success');
    if (invalidFiles.length > 0) {
        let sample = invalidFiles.slice(0, 3).join('、');
        if (invalidFiles.length > 3) sample += '…';
        setStatus(`⛔ 不支持的类型: ${sample}`, 'error');
    } else if (addedCount === 0 && invalidFiles.length === 0) {
        setStatus('ℹ️ 文件都已存在', 'info');
    }
}

function removeFileByIndex(indexToRemove) {
    if (indexToRemove >= 0 && indexToRemove < fileArray.length) {
        fileArray.splice(indexToRemove, 1);
        updateFileList();
        setStatus('🗑️ 文件已移除', 'info');
    }
}

function clearAllFiles() {
    if (fileArray.length === 0) return;
    fileArray = [];
    updateFileList();
    setStatus('🧹 列表已清空', 'info');
}

function updateFileList() {
    const container = document.getElementById('fileListContainer');
    container.innerHTML = renderFileList(fileArray);
}

// 预览功能
function openPreview(file) {
    const fileName = file.name;
    const ext = fileName.slice(fileName.lastIndexOf('.')).toLowerCase();
    document.getElementById('previewFileName').textContent = `预览: ${fileName}`;
    const previewContent = document.getElementById('previewContent');
    previewContent.innerHTML = '<div class="preview-placeholder">加载中...</div>';
    
    // 控制底部发送区域的显示 (默认隐藏)
    const footer = document.getElementById('previewFooter');
    footer.style.display = 'none';
    
    document.getElementById('previewModal').classList.add('active');

    if (ext === '.txt' || ext === '.md') {
        const reader = new FileReader();
        reader.onload = (e) => {
            previewContent.innerHTML = `<pre style="white-space: pre-wrap; font-family: monospace;">${escapeHtml(e.target.result)}</pre>`;
        };
        reader.onerror = () => {
            previewContent.innerHTML = '<div class="preview-placeholder">❌ 读取失败</div>';
        };
        reader.readAsText(file, 'UTF-8');
    }
    else if (ext === '.docx') {
        const reader = new FileReader();
        reader.onload = (e) => {
            const arrayBuffer = e.target.result;
            mammoth.convertToHtml({ arrayBuffer: arrayBuffer })
                .then(result => {
                    previewContent.innerHTML = `<div style="background:white; padding:1rem;">${result.value}</div>`;
                })
                .catch(err => {
                    previewContent.innerHTML = `<div class="preview-placeholder">❌ Word 解析失败: ${err.message}</div>`;
                });
        };
        reader.onerror = () => {
            previewContent.innerHTML = '<div class="preview-placeholder">❌ 读取文件失败</div>';
        };
        reader.readAsArrayBuffer(file);
    }
    else if (ext === '.xlsx') {
        const reader = new FileReader();
        reader.onload = (e) => {
            const data = new Uint8Array(e.target.result);
            const workbook = XLSX.read(data, { type: 'array' });
            const firstSheetName = workbook.SheetNames[0];
            const worksheet = workbook.Sheets[firstSheetName];
            const htmlTable = XLSX.utils.sheet_to_html(worksheet, { id: 'excel-table', editable: false });
            previewContent.innerHTML = htmlTable;
            
            // 在 reader.onload 内部，显示表格后绑定发送按钮
            // 显示发送区域
            footer.style.display = 'flex';

            // 绑定发送按钮事件（先移除旧监听，避免重复）
            const sendBtn = document.getElementById('sendTableDataBtn');
            const charInput = document.getElementById('standardCharInput');

            // 克隆替换以清除之前绑定的所有事件
            const newSendBtn = sendBtn.cloneNode(true);
            sendBtn.parentNode.replaceChild(newSendBtn, sendBtn);

            newSendBtn.addEventListener('click', () => {
                const standardChar = charInput.value.trim();
                if (!standardChar) {
                    alert('请输入标准字符', 'error');
                    return;
                }
                // 获取表格数据（二维数组）
                const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });

                // 动态导入 api 并调用 sendTableData
                import('../api/index.js').then(api => {
                    api.sendTableData({ 
                        fileName: file.name, 
                        sheetName: firstSheetName, 
                        data: jsonData, 
                        standardChar 
                    }).then(result => {
                        if (result.success) {
                            // 显示查找成功提示，包含找到的记录数
                            const foundCount = result.foundCount || 0;
                            alert(`✅ 查找成功，共找到 ${foundCount} 条记录`, 'success');
                        } else {
                            alert('❌ 发送失败: ' + (result.message || ''), 'error');
                        }
                    });
                }).catch(err => {
                    alert('❌ 导入API失败', 'error');
                });
            });
        };
        reader.onerror = () => {
            previewContent.innerHTML = '<div class="preview-placeholder">❌ 读取文件失败</div>';
        };
        reader.readAsArrayBuffer(file);
    }
    else {
        previewContent.innerHTML = '<div class="preview-placeholder">🔍 该文件类型暂不支持在线预览 (支持 .txt .md .docx .xlsx)</div>';
    }
}

// 指令执行
async function handleExecuteCommand() {
    const command = document.getElementById('commandInput').value.trim();
    if (!command) {
        setStatus('请输入指令', 'error');
        return;
    }

    const fileNames = fileArray.map(item => item.file.name);
    const result = await executeCommand(command, fileNames);  // 调用api

    const resultTitle = document.getElementById('resultTitle');
    const resultContent = document.getElementById('resultContent');
    if (result.success) {
        resultTitle.textContent = `执行指令: ${command}`;
        resultContent.innerHTML = `<pre style="white-space: pre-wrap; background: #1e293b; color: #bbf7d0; padding: 1rem; border-radius: 8px;">${escapeHtml(result.output)}</pre>`;
    } else {
        resultContent.innerHTML = `<div class="preview-placeholder">❌ 执行失败: ${escapeHtml(result.error)}</div>`;
    }
    document.getElementById('resultModal').classList.add('active');
    centerResultWindow();
}

// 个人资料更新
function updateProfileUI() {
    document.getElementById('avatarDisplay').src = currentAvatar;
    document.getElementById('profileNameDisplay').textContent = currentName;
    document.getElementById('avatarPreview').src = currentAvatar;
    document.getElementById('profileNameInput').value = currentName;
}

// 结果窗口居中
function centerResultWindow() {
    const modal = document.getElementById('resultModal');
    const content = document.getElementById('resultModalContent');
    if (!modal.classList.contains('active') || content.classList.contains('fullscreen')) return;
    const w = content.offsetWidth;
    const h = content.offsetHeight;
    const left = (window.innerWidth - w) / 2;
    const top = (window.innerHeight - h) / 2;
    content.style.left = Math.max(0, left) + 'px';
    content.style.top = Math.max(0, top) + 'px';
}

// 拖拽逻辑
function initDrag() {
    const header = document.getElementById('resultHeader');
    const content = document.getElementById('resultModalContent');
    let isDragging = false;
    let startX, startY, startLeft, startTop;

    header.addEventListener('mousedown', (e) => {
        if (e.target.closest('.fullscreen-btn') || e.target.closest('.delete-btn')) return;
        if (content.classList.contains('fullscreen')) return;

        e.preventDefault();
        isDragging = true;
        startX = e.clientX;
        startY = e.clientY;
        const rect = content.getBoundingClientRect();
        startLeft = rect.left;
        startTop = rect.top;
        content.style.cursor = 'move';
        content.style.transition = 'none';
    });

    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        e.preventDefault();
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;
        let newLeft = startLeft + dx;
        let newTop = startTop + dy;
        newLeft = Math.max(0, Math.min(window.innerWidth - content.offsetWidth, newLeft));
        newTop = Math.max(0, Math.min(window.innerHeight - content.offsetHeight, newTop));
        content.style.left = newLeft + 'px';
        content.style.top = newTop + 'px';
    });

    document.addEventListener('mouseup', () => {
        if (isDragging) {
            isDragging = false;
            content.style.cursor = '';
            content.style.transition = '';
        }
    });
}

// 页面初始化
document.addEventListener('DOMContentLoaded', () => {
    const app = document.getElementById('app');
    app.innerHTML = `
        <!-- 个人中心 -->
        ${renderProfileCorner({ avatar: currentAvatar, name: currentName })}
        <!-- 主卡片 -->
        <div class="upload-card">
            <h2>📁 文件上传 & 指令执行</h2>
            <div class="subhead">支持 .txt · .md · .doc/.docx · .xls/.xlsx (旧版Word/Excel可上传，预览限新版)</div>
            <input type="file" id="fileInput" multiple
                accept=".txt,.md,.doc,.docx,.xls,.xlsx,text/plain,text/markdown,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                style="display: none;">
            <div class="file-actions">
                <button class="btn" id="selectBtn">📂 选择文件</button>
                <button class="btn btn-secondary" id="clearAllBtn">🗑️ 清空列表</button>
            </div>
            <div id="dropZone" class="drop-zone">⬇️ 或将文件拖放到这里 (支持旧版.doc/.xls)</div>
            <div id="fileListContainer" class="file-list"></div>
            <div class="upload-area">
                <button class="btn btn-primary" id="uploadBtn">🚀 模拟上传</button>
                <span id="statusMsg" class="status">就绪，可添加文件</span>
                ${renderCommandInput()}
            </div>
        </div>
        <!-- 模态框 -->
        ${renderProfileModal()}
        ${renderPreviewModal()}
        ${renderResultModal()}
    `;

    // 绑定元素引用
    elements = {
        fileInput: document.getElementById('fileInput'),
        selectBtn: document.getElementById('selectBtn'),
        clearAllBtn: document.getElementById('clearAllBtn'),
        dropZone: document.getElementById('dropZone'),
        uploadBtn: document.getElementById('uploadBtn'),
        commandInput: document.getElementById('commandInput'),
        executeBtn: document.getElementById('executeBtn'),
        avatarDisplay: document.getElementById('avatarDisplay'),
        editProfileBtn: document.getElementById('editProfileBtn'),
        profileModal: document.getElementById('profileModal'),
        closeProfileModal: document.getElementById('closeProfileModal'),
        saveProfileBtn: document.getElementById('saveProfileBtn'),
        avatarUpload: document.getElementById('avatarUpload'),
        uploadAvatarBtn: document.getElementById('uploadAvatarBtn'),
        avatarPreview: document.getElementById('avatarPreview'),
        profileNameInput: document.getElementById('profileNameInput'),
        previewModal: document.getElementById('previewModal'),
        closePreviewBtn: document.getElementById('closePreviewBtn'),
        fullscreenPreviewBtn: document.getElementById('fullscreenPreviewBtn'),
        previewModalContent: document.getElementById('previewModalContent'),
        resultModal: document.getElementById('resultModal'),
        closeResultBtn: document.getElementById('closeResultBtn'),
        fullscreenResultBtn: document.getElementById('fullscreenResultBtn'),
        resultModalContent: document.getElementById('resultModalContent')
    };

    // 初始化个人资料UI
    updateProfileUI();

    // 文件上传事件
    elements.selectBtn.addEventListener('click', () => {
        elements.fileInput.value = '';
        elements.fileInput.click();
    });
    elements.fileInput.addEventListener('change', (e) => addFiles(e.target.files));

    // 拖拽
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        document.addEventListener(eventName, (e) => e.preventDefault());
        elements.dropZone.addEventListener(eventName, (e) => e.preventDefault());
    });
    elements.dropZone.addEventListener('dragover', () => elements.dropZone.classList.add('dragover'));
    elements.dropZone.addEventListener('dragleave', () => elements.dropZone.classList.remove('dragover'));
    elements.dropZone.addEventListener('drop', (e) => {
        elements.dropZone.classList.remove('dragover');
        const items = e.dataTransfer?.files;
        if (items && items.length > 0) addFiles(items);
        else setStatus('⚠️ 未检测到文件', 'error');
    });
    elements.dropZone.addEventListener('click', () => {
        elements.fileInput.value = '';
        elements.fileInput.click();
    });

    // 清空
    elements.clearAllBtn.addEventListener('click', clearAllFiles);

    // 文件列表事件委托 (预览/删除)
    document.getElementById('fileListContainer').addEventListener('click', (e) => {
        const deleteBtn = e.target.closest('.delete-btn');
        if (deleteBtn) {
            e.preventDefault();
            const index = deleteBtn.getAttribute('data-index');
            if (index !== null) removeFileByIndex(parseInt(index, 10));
            return;
        }
        const previewBtn = e.target.closest('.preview-text-btn');
        if (previewBtn) {
            e.preventDefault();
            const index = previewBtn.getAttribute('data-index');
            if (index !== null) {
                const fileItem = fileArray[parseInt(index, 10)];
                if (fileItem) openPreview(fileItem.file);
            }
        }
    });

    // 模拟上传按钮 (调用api)
    elements.uploadBtn.addEventListener('click', async () => {
        if (fileArray.length === 0) {
            setStatus('⚠️ 没有可上传的文件', 'error');
            return;
        }
        const files = fileArray.map(item => item.file);
        const result = await uploadFiles(files);
        if (result.success) {
            setStatus(`✅ 上传成功 (${files.length} 个文件)`, 'success');
        } else {
            setStatus(`❌ 上传失败: ${result.message}`, 'error');
        }
    });

    // 指令执行
    elements.executeBtn.addEventListener('click', handleExecuteCommand);
    elements.commandInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleExecuteCommand();
    });

    // 个人中心交互
    elements.editProfileBtn.addEventListener('click', () => {
        elements.avatarPreview.src = currentAvatar;
        elements.profileNameInput.value = currentName;
        elements.profileModal.classList.add('active');
    });
    elements.closeProfileModal.addEventListener('click', () => {
        elements.profileModal.classList.remove('active');
    });
    elements.uploadAvatarBtn.addEventListener('click', () => elements.avatarUpload.click());
    elements.avatarUpload.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;
        if (!file.type.startsWith('image/')) {
            setStatus('请选择图片文件', 'error');
            return;
        }
        const reader = new FileReader();
        reader.onload = (ev) => {
            currentAvatar = ev.target.result;
            elements.avatarPreview.src = currentAvatar;
        };
        reader.readAsDataURL(file);
    });
    elements.saveProfileBtn.addEventListener('click', () => {
        const newName = elements.profileNameInput.value.trim();
        if (newName) currentName = newName;
        updateProfileUI();
        elements.profileModal.classList.remove('active');
        setStatus('✅ 个人资料已更新', 'success');
    });
    elements.avatarDisplay.addEventListener('click', () => elements.avatarUpload.click());
    elements.avatarUpload.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file || !file.type.startsWith('image/')) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            currentAvatar = ev.target.result;
            elements.avatarDisplay.src = currentAvatar;
        };
        reader.readAsDataURL(file);
        setStatus('头像已更新', 'success');
        elements.avatarUpload.value = '';
    });
    elements.profileModal.addEventListener('click', (e) => {
        if (e.target === elements.profileModal) elements.profileModal.classList.remove('active');
    });

    // 预览模态框控制
    elements.closePreviewBtn.addEventListener('click', () => {
        elements.previewModal.classList.remove('active');
        if (document.fullscreenElement) document.exitFullscreen();
    });
    elements.previewModal.addEventListener('click', (e) => {
        if (e.target === elements.previewModal) {
            elements.previewModal.classList.remove('active');
            if (document.fullscreenElement) document.exitFullscreen();
        }
    });
    elements.fullscreenPreviewBtn.addEventListener('click', () => toggleFullscreen(elements.previewModalContent));

    // 结果模态框控制
    elements.closeResultBtn.addEventListener('click', () => {
        elements.resultModal.classList.remove('active');
        if (document.fullscreenElement) document.exitFullscreen();
    });
    elements.resultModal.addEventListener('click', (e) => {
        if (e.target === elements.resultModal) {
            elements.resultModal.classList.remove('active');
            if (document.fullscreenElement) document.exitFullscreen();
        }
    });
    elements.fullscreenResultBtn.addEventListener('click', () => toggleFullscreen(elements.resultModalContent));

    // 全屏变化监听
    document.addEventListener('fullscreenchange', () => {
        if (document.fullscreenElement === elements.previewModalContent) {
            elements.previewModalContent.classList.add('fullscreen');
        } else {
            elements.previewModalContent.classList.remove('fullscreen');
        }
        if (document.fullscreenElement === elements.resultModalContent) {
            elements.resultModalContent.classList.add('fullscreen');
        } else {
            elements.resultModalContent.classList.remove('fullscreen');
            if (elements.resultModal.classList.contains('active')) {
                centerResultWindow();
            }
        }
    });

    // 窗口resize时重绘结果窗口位置
    window.addEventListener('resize', () => {
        if (elements.resultModal.classList.contains('active') && !elements.resultModalContent.classList.contains('fullscreen')) {
            centerResultWindow();
        }
    });

    // 初始化拖拽
    initDrag();

    // 初始文件列表渲染
    updateFileList();
});