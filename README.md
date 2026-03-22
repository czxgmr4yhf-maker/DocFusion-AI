# DocFusion-AI
服创赛-A23，大语言模型驱动的文档理解与多源数据融合系统
标题、上下标等就不考虑了，最后json文件就用"A23 竞赛执行方案.pdf"里面的4个字段
"doc_id"
"paragraphs"
"tables"
"raw_text"
项目结构：

backend/      后端服务（FastAPI）
frontend/     前端代码
docs/         项目文档与开发笔记
demo/         演示材料

backend/app/
    api/      接口层
    core/     核心配置与日志
    db/       数据库相关
    services/ 业务逻辑
