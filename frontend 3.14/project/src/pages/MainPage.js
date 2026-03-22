import { renderProfileCorner } from '../components/ProfileCorner.js';
import { renderProfileModal } from '../components/ProfileModal.js';
import { renderPreviewModal } from '../components/PreviewModal.js';
import { renderResultModal } from '../components/ResultModal.js';
import { renderCommandInput } from '../components/CommandInput.js';
import { renderFileList } from '../components/FileList.js';
import { uploadFiles, executeCommand, getTask, getFields } from '../api/index.js';
import { escapeHtml, toggleFullscreen } from '../utils/helpers.js';

let fileArray = [];
let currentAvatar = 'data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'40\' height=\'40\' viewBox=\'0 0 24 24\' fill=\'%2394a3b8\'%3E%3Cpath d=\'M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z\'/%3E%3C/svg%3E';
let currentName = '旅行者';

// DOM元素引用
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

function readFileAsText(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = e => resolve(e.target.result);
        reader.onerror = e => reject(e.target.error);
        reader.readAsText(file, 'UTF-8');
    });
}

function readFileAsArrayBuffer(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = e => resolve(e.target.result);
        reader.onerror = e => reject(e.target.error);
        reader.readAsArrayBuffer(file);
    });
}

function extractFieldsFromText(text) {
    const lines = text.split(/\r?\n/);
    const fields = new Set();
    lines.forEach(line => {
        line = line.trim();
        if (line) {
            const firstWord = line.split(/\s+/)[0];
            if (firstWord && firstWord.length > 0 && firstWord.length < 30) {
                fields.add(firstWord);
            }
        }
    });
    return Array.from(fields);
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

            footer.style.display = 'flex';

            const sendBtn = document.getElementById('sendTableDataBtn');
            const charInput = document.getElementById('standardCharInput');

            const newSendBtn = sendBtn.cloneNode(true);
            sendBtn.parentNode.replaceChild(newSendBtn, sendBtn);

            newSendBtn.addEventListener('click', () => {
                const standardChar = charInput.value.trim();
                if (!standardChar) {
                    alert('请输入标准字符');
                    return;
                }

                const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });

                import('../api/index.js').then(api => {
                    api.sendTableData({
                        fileName: file.name,
                        sheetName: firstSheetName,
                        data: jsonData,
                        standardChar
                    }).then(result => {
                        if (result.success) {
                            const foundCount = result.foundCount || 0;
                            alert(`✅ 查找成功，共找到 ${foundCount} 条记录`);
                        } else {
                            alert('❌ 发送失败: ' + (result.message || ''));
                        }
                    });
                }).catch(() => {
                    alert('❌ 导入API失败');
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

async function extractFields(file) {
    const fileName = file.name;
    const ext = fileName.slice(fileName.lastIndexOf('.')).toLowerCase();
    
    // 显示加载中
    document.getElementById('resultTitle').textContent = `字段抽取: ${fileName}`;
    document.getElementById('resultContent').innerHTML = '<div class="preview-placeholder">抽取中...</div>';
    document.getElementById('resultModal').classList.add('active');
    centerResultWindow();

    let fields = [];

    try {
        if (ext === '.txt' || ext === '.md') {
            const text = await readFileAsText(file);
            fields = extractFieldsFromText(text);
        } else if (ext === '.docx') {
            const arrayBuffer = await readFileAsArrayBuffer(file);
            const result = await mammoth.extractRawText({ arrayBuffer });
            fields = extractFieldsFromText(result.value);
        } else if (ext === '.xlsx') {
            const arrayBuffer = await readFileAsArrayBuffer(file);
            const workbook = XLSX.read(new Uint8Array(arrayBuffer), { type: 'array' });
            const firstSheetName = workbook.SheetNames[0];
            const worksheet = workbook.Sheets[firstSheetName];
            const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
            if (jsonData.length > 0) {
                fields = jsonData[0].filter(cell => cell != null && cell.toString().trim() !== '');
            } else {
                fields = [];
            }
        } else {
            fields = ['不支持的文件类型'];
        }

        // 去重并限制数量
        fields = [...new Set(fields)].slice(0, 50);

        // 构建结果显示
        const fieldsHtml = fields.map(f => `<div style="padding: 4px 8px; background: #f1f5f9; border-radius: 20px; margin: 4px;">${escapeHtml(f)}</div>`).join('');
        const sendButtonId = 'sendFieldsBtn_' + Date.now();
        document.getElementById('resultContent').innerHTML = `
            <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px;">${fieldsHtml}</div>
            <div style="display: flex; gap: 10px; align-items: center; border-top: 1px solid #e2e8f0; padding-top: 16px;">
                <input type="text" id="extraParamInput" class="command-input" placeholder="额外参数(可选)" style="flex:1;">
                <button class="btn btn-primary" id="${sendButtonId}">发送字段结果</button>
            </div>
        `;

        // 绑定发送按钮事件
        document.getElementById(sendButtonId).addEventListener('click', async () => {
            const extraParam = document.getElementById('extraParamInput').value.trim();
            const { sendExtractedFields } = await import('../api/index.js');
            const result = await sendExtractedFields({
                fileName: file.name,
                fields: fields,
                extra: extraParam
            });
            if (result.success) {
                setStatus(`✅ 字段结果发送成功，共 ${fields.length} 个字段`, 'success');
            } else {
                setStatus('❌ 发送失败: ' + (result.message || ''), 'error');
            }
        });

    } catch (err) {
        document.getElementById('resultContent').innerHTML = `<div class="preview-placeholder">❌ 抽取失败: ${escapeHtml(err.message)}</div>`;
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
    const result = await executeCommand(command, fileNames);

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
        ${renderProfileCorner({ avatar: currentAvatar, name: currentName })}
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
                <button class="btn btn-primary" id="uploadBtn">🚀 上传文件</button>
                <span id="statusMsg" class="status">就绪，可添加文件</span>
                ${renderCommandInput()}
            </div>
        </div>
        ${renderProfileModal()}
        ${renderPreviewModal()}
        ${renderResultModal()}
    `;

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
        const extractBtn = e.target.closest('.extract-btn');
        if (extractBtn) {
            e.preventDefault();
            const index = extractBtn.getAttribute('data-index');
            if (index !== null) {
                const fileItem = fileArray[parseInt(index, 10)];
                if (fileItem) extractFields(fileItem.file);
            }
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

        const uploadResult = await uploadFiles(files);

        if (!uploadResult.success) {
            setStatus(`❌ 上传失败: ${uploadResult.message}`, 'error');
            return;
        }

        const firstTaskId = uploadResult.results?.[0]?.task_id;
        if (!firstTaskId) {
            setStatus('❌ 上传成功，但没有拿到 task_id', 'error');
            return;
        }

        setStatus(`✅ 上传成功，正在查询任务 ${firstTaskId}...`, 'success');

        const taskResult = await getTask(firstTaskId);

        if (!taskResult.success) {
            setStatus(`❌ 查询任务失败: ${taskResult.message}`, 'error');
            return;
        }

        const status = taskResult.data.status || '未知状态';
        setStatus(`✅ 任务 ${firstTaskId} 状态：${status}，正在查询字段结果...`, 'success');

        const fieldsResult = await getFields(firstTaskId);

        if (fieldsResult.success) {
            const data = fieldsResult.data;
            const resultTitle = document.getElementById('resultTitle');
            const resultContent = document.getElementById('resultContent');

            resultTitle.textContent = `字段提取结果（任务 ${firstTaskId}）`;
            resultContent.innerHTML = `
                <div style="background:#fff; padding:1rem; border-radius:8px; line-height:1.8;">
                    <p><strong>任务ID：</strong>${data.task_id ?? ''}</p>
                    <p><strong>文档ID：</strong>${data.doc_id ?? ''}</p>
                    <p><strong>文档类型：</strong>${data.doc_type ?? ''}</p>
                    <p><strong>项目名称：</strong>${data.project_name ?? ''}</p>
                    <p><strong>项目负责人：</strong>${data.project_leader ?? ''}</p>
                    <p><strong>机构名称：</strong>${data.organization_name ?? ''}</p>
                    <p><strong>联系电话：</strong>${data.phone ?? ''}</p>
                </div>
            `;

            document.getElementById('resultModal').classList.add('active');
            centerResultWindow();
            setStatus(`✅ 字段结果获取成功（任务 ${firstTaskId}）`, 'success');
            console.log('字段结果：', data);
        } else {
            setStatus(`⚠️ 任务已上传，但暂未查到字段结果: ${fieldsResult.message}`, 'error');
        }
    });

    elements.executeBtn.addEventListener('click', handleExecuteCommand);
    elements.commandInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleExecuteCommand();
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
