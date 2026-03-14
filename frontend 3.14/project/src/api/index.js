//API封装请求
/**
 * 模拟文件上传 (未来对接后端)
 * @param {File[]} files
 * @returns {Promise<{success: boolean, message?: string}>}
 */
export function uploadFiles(files) {
    // ========= 未来后端对接点 =========
    // const formData = new FormData();
    // files.forEach(file => formData.append('files', file));
    // return fetch('/api/upload', { method: 'POST', body: formData })
    //   .then(res => res.json())
    //   .then(data => ({ success: true, ...data }))
    //   .catch(err => ({ success: false, message: err.message }));
    // =================================
    return new Promise(resolve => {
        setTimeout(() => {
            console.log('【模拟上传】', files.map(f => f.name));
            resolve({ success: true, message: '模拟上传成功' });
        }, 500);
    });
}

/**
 * 执行指令 (未来对接后端算法)
 * @param {string} command
 * @param {string[]} [fileNames] - 当前文件列表，可选
 * @returns {Promise<{success: boolean, output?: string, error?: string}>}
 */
export function executeCommand(command, fileNames = []) {
    // ========= 未来后端对接点 =========
    // return fetch('/api/execute', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ command, files: fileNames })
    // })
    // .then(res => res.json())
    // .then(data => ({ success: true, output: data.output }))
    // .catch(err => ({ success: false, error: err.message }));
    // =================================
    return new Promise(resolve => {
        setTimeout(() => {
            const mockOutput = [
                `> ${command}`,
                '执行中...',
                '----------------------------------------',
                '模拟终端输出',
                '当前工作目录: /home/user',
                '文件列表:',
                ...fileNames.map(name => `  ${name}`),
                `命令 "${command}" 已完成，退出代码 0`,
                `[完成于 ${new Date().toLocaleTimeString()}]`
            ].join('\n');
            resolve({ success: true, output: mockOutput });
        }, 600);
    });
}

/**
 * 发送表格数据（标准字符 + 表格内容）
 * @param {Object} payload
 * @param {string} payload.fileName - 原文件名
 * @param {string} payload.sheetName - 工作表名
 * @param {Array<Array>} payload.data - 表格二维数组数据
 * @param {string} payload.standardChar - 用户输入的标准字符
 * @returns {Promise<{success: boolean, foundCount?: number, message?: string}>}
 */
export function sendTableData(payload) {
    // ========= 未来后端对接点 =========
    // return fetch('/api/table-data', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify(payload)
    // })
    // .then(res => res.json())
    // .then(data => ({ success: true, foundCount: data.count }))
    // .catch(err => ({ success: false, message: err.message }));
    // =================================
    return new Promise(resolve => {
        // 模拟网络延迟
        setTimeout(() => {
            // 随机生成一个 1～10 的查找结果数
            const foundCount = Math.floor(Math.random() * 10) + 1;
            console.log('【发送表格数据】', payload, '模拟找到', foundCount, '条记录');
            resolve({ 
                success: true, 
                foundCount, 
                message: `模拟查找成功，找到 ${foundCount} 条记录` 
            });
        }, 600);
    });
}