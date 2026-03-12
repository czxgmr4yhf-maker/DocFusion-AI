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