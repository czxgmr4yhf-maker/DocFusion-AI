import { renderProfileCorner } from '../components/ProfileCorner.js';
import { renderProfileModal } from '../components/ProfileModal.js';
import { renderPreviewModal } from '../components/PreviewModal.js';
import { renderResultModal } from '../components/ResultModal.js';
import { renderFileList } from '../components/FileList.js';
import { uploadFiles, getTask, getFields} from '../api/index.js';
import { escapeHtml, toggleFullscreen } from '../utils/helpers.js';

// 全局状态
let fileArray = [];
let currentAvatar = 'data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'40\' height=\'40\' viewBox=\'0 0 24 24\' fill=\'%2394a3b8\'%3E%3Cpath d=\'M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z\'/%3E%3C/svg%3E';
let currentName = '旅行者';

// DOM元素引用
let elements = {};

// 允许的扩展名
const allowedExtensions = ['.txt', '.md', '.docx', '.xlsx'];

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
        ${renderProfileCorner({ avatar: currentAvatar, name: currentName })}
        <div class="upload-card">
            <h2>📁 文件上传</h2>
            <div class="subhead">支持 .txt · .md · .docx · .xlsx</div>
            <input type="file" id="fileInput" multiple
                accept=".txt,.md,.doc,.docx,.xls,.xlsx,text/plain,text/markdown,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                style="display: none;">
            <div class="file-actions">
                <button class="btn" id="selectBtn">📂 选择文件</button>
                <button class="btn btn-secondary" id="clearAllBtn">🗑️ 清空列表</button>
            </div>
            <div id="dropZone" class="drop-zone">⬇️ 或将文件拖放到这里</div>
            <div id="fileListContainer" class="file-list"></div>
            <div class="upload-area">
                <button class="btn btn-primary" id="uploadBtn">🚀 上传文件</button>
                <span id="statusMsg" class="status">就绪，可添加文件</span>
            </div>
        </div>
        ${renderProfileModal()}
        ${renderPreviewModal()}
        ${renderResultModal()}
        <!-- 新增字段溯源模态框 -->
        <div class="modal" id="sourceModal">
            <div class="modal-content" style="max-width: 600px;">
                <div class="preview-header">
                    <span id="sourceModalTitle">字段溯源</span>
                    <button class="delete-btn" id="closeSourceModalBtn" style="font-size:1.5rem;">&times;</button>
                </div>
                <div class="preview-content" id="sourceContent" style="max-height: 400px;">
                    <!-- 溯源信息将显示在这里 -->
                </div>
            </div>
        </div>
    `;

    elements = {
        fileInput: document.getElementById('fileInput'),
        selectBtn: document.getElementById('selectBtn'),
        clearAllBtn: document.getElementById('clearAllBtn'),
        dropZone: document.getElementById('dropZone'),
        uploadBtn: document.getElementById('uploadBtn'),
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
        resultModalContent: document.getElementById('resultModalContent'),
        // 新增：溯源模态框相关元素
        sourceModal: document.getElementById('sourceModal'),
        closeSourceModalBtn: document.getElementById('closeSourceModalBtn'),
        sourceContent: document.getElementById('sourceContent'),
        sourceModalTitle: document.getElementById('sourceModalTitle')
    };

    document.body.addEventListener('click', async (e) => {
        const target = e.target.closest('.source-field');
        if (!target) return;
        const taskId = target.getAttribute('data-task-id');
        const fieldName = target.getAttribute('data-field-name');
        if (!taskId || !fieldName) return;

        // 显示加载状态
        const sourceModal = document.getElementById('sourceModal');
        const sourceContent = document.getElementById('sourceContent');
        const sourceModalTitle = document.getElementById('sourceModalTitle');
        sourceModalTitle.textContent = `字段溯源: ${fieldName}`;
        sourceContent.innerHTML = '<div class="preview-placeholder">加载中...</div>';
        sourceModal.classList.add('active');

        // 调用溯源接口
        const { getFieldSource } = await import('../api/index.js');
        const result = await getFieldSource(taskId, fieldName);
        if (result.success) {
            const data = result.data;
            let html = `
                <div style="margin-bottom: 12px;"><strong>来源文件：</strong> ${escapeHtml(data.source_file || '未知')}</div>
                <div style="margin-bottom: 12px;"><strong>所在段落：</strong></div>
                <pre style="background:#f8fafc; padding:12px; border-radius:8px; margin-bottom:12px;">${escapeHtml(data.source_paragraph || '无')}</pre>
                <div style="margin-bottom: 12px;"><strong>原始文本：</strong></div>
                <pre style="background:#f8fafc; padding:12px; border-radius:8px;">${escapeHtml(data.source_text || '无')}</pre>
            `;
            sourceContent.innerHTML = html;
        } else {
            sourceContent.innerHTML = `<div class="preview-placeholder">❌ 获取溯源失败: ${escapeHtml(result.message)}</div>`;
        }
    });

    updateProfileUI();

    elements.selectBtn.addEventListener('click', () => {
        elements.fileInput.value = '';
        elements.fileInput.click();
    });
    elements.fileInput.addEventListener('change', (e) => addFiles(e.target.files));

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

    elements.clearAllBtn.addEventListener('click', clearAllFiles);

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

    // 上传按钮：上传 -> 查询任务 -> 查询字段
    elements.uploadBtn.addEventListener('click', async () => {
    if (fileArray.length === 0) {
        setStatus('⚠️ 没有可上传的文件', 'error');
        return;
    }

    const files = fileArray.map(item => item.file);
    setStatus('⏳ 上传中...', 'info');

    // 1. 上传所有文件，获取 task_id 列表
    const uploadResult = await uploadFiles(files);
    if (!uploadResult.success) {
        setStatus(`❌ 上传失败: ${uploadResult.message}`, 'error');
        return;
    }

    const tasks = uploadResult.results; // 每个元素包含 fileName 和 task_id
    if (!tasks || tasks.length === 0) {
        setStatus('❌ 上传成功，但没有返回任务信息', 'error');
        return;
    }

    setStatus(`✅ 上传成功，共 ${tasks.length} 个任务`, 'success');

    // 2. 准备结果窗口
    const resultTitle = document.getElementById('resultTitle');
    const resultContent = document.getElementById('resultContent');
    resultTitle.textContent = '文件解析与字段提取结果';
    resultContent.innerHTML = '<div class="preview-placeholder">正在获取字段结果，请稍候...</div>';
    document.getElementById('resultModal').classList.add('active');
    centerResultWindow();

    // 3. 依次处理每个任务（轮询状态 → 获取字段）
    const allFields = [];
    for (let i = 0; i < tasks.length; i++) {
        const task = tasks[i];
        const taskId = task.task_id;
        const fileName = task.fileName;

        // 更新进度提示
        resultContent.innerHTML = `<div class="preview-placeholder">正在处理 (${i+1}/${tasks.length})：${escapeHtml(fileName)}<br>请稍候...</div>`;

        // 轮询任务状态，直到完成或超时
        let taskCompleted = false;
        let retries = 0;
        const maxRetries = 30;  // 最多等待 30 秒
        const interval = 1000;  // 每秒查询一次

        while (!taskCompleted && retries < maxRetries) {
            const taskRes = await getTask(taskId);
            if (!taskRes.success) {
                break;
            }
            const status = taskRes.data?.status;
            if (status === 'extracted') {
                taskCompleted = true;
                break;
            }
            retries++;
            await new Promise(resolve => setTimeout(resolve, interval));
        }

        if (!taskCompleted) {
            allFields.push({
                fileName,
                success: false,
                error: '任务未完成或超时'
            });
            continue;
        }

        // 获取字段结果
        const fieldsRes = await getFields(taskId);
        if (fieldsRes.success) {
            allFields.push({
                fileName,
                success: true,
                data: fieldsRes.data
            });
        } else {
            allFields.push({
                fileName,
                success: false,
                error: fieldsRes.message
            });
        }
    }

    // 4. 汇总展示所有结果
    let resultHtml = `
        <div style="background: #f0f9ff; padding: 12px; border-radius: 8px; margin-bottom: 16px;">
            <div style="font-weight: 600;">📊 处理完成</div>
            <div>共 ${tasks.length} 个文件，成功 ${allFields.filter(f => f.success).length} 个，失败 ${allFields.filter(f => !f.success).length} 个</div>
        </div>
    `;

   allFields.forEach(field => {
    const taskId = field.data.task_id;  // 确保后端返回中包含 task_id
    resultHtml += `
        <div style="margin-bottom: 20px; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
            <div style="background: ${field.success ? '#f1f5f9' : '#fee2e2'}; padding: 8px 12px; font-weight: 600;">
                📄 ${escapeHtml(field.fileName)} ${field.success ? '✅' : '❌'}
            </div>
                <div style="padding: 12px;">
                    ${field.success ? `
                        <p><strong>任务ID：</strong><span class="source-field" data-task-id="${taskId}" data-field-name="task_id" style="color:#2563eb; cursor:pointer; text-decoration:underline;">${field.data.task_id ?? ''}</p></span>
                        <p><strong>文档ID：</strong><span class="source-field" data-task-id="${taskId}" data-field-name="doc_id" style="color:#2563eb; cursor:pointer; text-decoration:underline;">${field.data.doc_id ?? ''}</p>
                        <p><strong>文档类型：</strong> <span class="source-field" data-task-id="${taskId}" data-field-name="doc_type" style="color:#2563eb; cursor:pointer; text-decoration:underline;">${field.data.doc_type ?? ''}</p>
                        <p><strong>项目名称：</strong> <span class="source-field" data-task-id="${taskId}" data-field-name="project_name" style="color:#2563eb; cursor:pointer; text-decoration:underline;">${field.data.project_name ?? ''}</p>
                        <p><strong>项目负责人：</strong> <span class="source-field" data-task-id="${taskId}" data-field-name="project_leader" style="color:#2563eb; cursor:pointer; text-decoration:underline;">${field.data.project_leader ?? ''}</p>
                        <p><strong>机构名称：</strong> <span class="source-field" data-task-id="${taskId}" data-field-name="organization_name" style="color:#2563eb; cursor:pointer; text-decoration:underline;">${field.data.organization_name ?? ''}</p>
                        <p><strong>联系电话：</strong> <span class="source-field" data-task-id="${taskId}" data-field-name="phone" style="color:#2563eb; cursor:pointer; text-decoration:underline;">${field.data.phone ?? ''}</p>
                        <details>
                            <summary style="cursor:pointer; color:#3b82f6;">📄 查看原始文本摘要</summary>
                            <pre style="white-space: pre-wrap; background:#f8fafc; padding:8px; border-radius:4px; margin-top:8px;">${escapeHtml((field.data.raw_text || '').slice(0, 500))}${(field.data.raw_text || '').length > 500 ? '...' : ''}</pre>
                        </details>
                    ` : `
                        <div style="color: #b91c1c;">❌ 获取字段失败: ${escapeHtml(field.error)}</div>
                    `}
                </div>
            </div>
        `;
    });

    resultContent.innerHTML = resultHtml;
    setStatus(`✅ 处理完成，成功 ${allFields.filter(f => f.success).length} 个文件`, 'success');
});

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

    // 关闭溯源模态框
    if (elements.closeSourceModalBtn) {
        elements.closeSourceModalBtn.addEventListener('click', () => {
            elements.sourceModal.classList.remove('active');
        });
    }
    if (elements.sourceModal) {
        elements.sourceModal.addEventListener('click', (e) => {
            if (e.target === elements.sourceModal) {
                elements.sourceModal.classList.remove('active');
            }
        });
    }

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

    window.addEventListener('resize', () => {
        if (elements.resultModal.classList.contains('active') && !elements.resultModalContent.classList.contains('fullscreen')) {
            centerResultWindow();
        }
    });

    initDrag();
    updateFileList();
});