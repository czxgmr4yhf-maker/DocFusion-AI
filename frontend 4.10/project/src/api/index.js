const BASE_URL = 'http://127.0.0.1:8000';

/**
 * 真实文件上传
 * @param {File[]} files
 * @returns {Promise<{success: boolean, message?: string, results?: any[]}>}
 */
export async function uploadFiles(files) {
    try {
        const results = [];

        for (const file of files) {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`${BASE_URL}/upload`, {
                method: 'POST',
                body: formData
            });

            const text = await response.text();
            console.log('上传响应状态:', response.status);
            console.log('上传响应原文:', text);

            let data;
            try {
                data = JSON.parse(text);
            } catch (e) {
                throw new Error(`后端返回的不是合法 JSON：${text}`);
            }

            if (!response.ok) {
                throw new Error(`上传失败，状态码：${response.status}，响应：${text}`);
            }

            results.push({
                fileName: file.name,
                ...data
            });
        }

        console.log('【真实上传成功】', results);

        return {
            success: true,
            message: '文件上传成功',
            results
        };
    } catch (err) {
        console.error('【上传失败】', err);
        return {
            success: false,
            message: err.message || '上传失败'
        };
    }
}

/**
 * 查询任务状态
 * @param {number|string} taskId
 * @returns {Promise<{success: boolean, data?: any, message?: string}>}
 */
export async function getTask(taskId) {
    try {
        const response = await fetch(`${BASE_URL}/tasks/${taskId}`, {
            method: 'GET'
        });

        const text = await response.text();
        console.log('任务查询响应状态:', response.status);
        console.log('任务查询响应原文:', text);

        let data;
        try {
            data = JSON.parse(text);
        } catch (e) {
            throw new Error(`后端返回的不是合法 JSON：${text}`);
        }

        if (!response.ok) {
            throw new Error(`查询任务失败，状态码：${response.status}，响应：${text}`);
        }

        return {
            success: true,
            data
        };
    } catch (err) {
        console.error('【查询任务失败】', err);
        return {
            success: false,
            message: err.message || '查询任务失败'
        };
    }
}

/**
 * 查询字段提取结果
 * @param {number|string} taskId
 * @returns {Promise<{success: boolean, data?: any, message?: string}>}
 */
export async function getFields(taskId) {
    try {
        const response = await fetch(`${BASE_URL}/fields/${taskId}`, {
            method: 'GET'
        });

        const text = await response.text();
        console.log('字段查询响应状态:', response.status);
        console.log('字段查询响应原文:', text);

        let data;
        try {
            data = JSON.parse(text);
        } catch (e) {
            throw new Error(`后端返回的不是合法 JSON：${text}`);
        }

        if (!response.ok) {
            throw new Error(`查询字段结果失败，状态码：${response.status}，响应：${text}`);
        }

        return {
            success: true,
            data
        };
    } catch (err) {
        console.error('【查询字段结果失败】', err);
        return {
            success: false,
            message: err.message || '查询字段结果失败'
        };
    }
}

/**
 * 获取字段溯源信息
 * @param {number|string} taskId
 * @param {string} fieldName - 字段名，如 'project_name', 'project_leader', 'organization_name', 'phone'
 * @returns {Promise<{success: boolean, data?: any, message?: string}>}
 */
export async function getFieldSource(taskId, fieldName) {
    try {
        const response = await fetch(`${BASE_URL}/fields/${taskId}/source/${fieldName}`, {
            method: 'GET'
        });
        const text = await response.text();
        let data;
        try {
            data = JSON.parse(text);
        } catch (e) {
            throw new Error(`后端返回不是合法 JSON: ${text}`);
        }
        if (!response.ok) {
            throw new Error(`查询溯源失败，状态码：${response.status}`);
        }
        return { success: true, data };
    } catch (err) {
        console.error('【获取字段溯源失败】', err);
        return { success: false, message: err.message };
    }
}
