//工具函数
/**
 * 转义HTML特殊字符，防止XSS
 * @param {string} unsafe
 * @returns {string}
 */
export function escapeHtml(unsafe) {
    return unsafe.replace(/[&<>"]/g, (m) => {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        if (m === '"') return '&quot;';
        return m;
    });
}

/**
 * 格式化文件大小
 * @param {number} bytes
 * @returns {string}
 */
export function formatFileSize(bytes) {
    if (bytes === 0) return '0 KB';
    const kb = bytes / 1024;
    return kb.toFixed(1) + ' KB';
}

/**
 * 全屏切换
 * @param {HTMLElement} element
 */
export function toggleFullscreen(element) {
    if (!document.fullscreenElement) {
        element.requestFullscreen().catch(err => {
            console.error('全屏失败:', err);
        });
    } else {
        document.exitFullscreen();
    }
}