# Extract 模块说明

## 模块目标

当前 `extract` 目录实现的是第一版字段抽取流程，输入为解析后的 `data.json`，输出为简洁的抽取结果 JSON。

这一版采用两阶段思路：

- 实体类字段：先做候选定位，再用大模型在候选中选择最终值
- 规则类字段：先在句子级别召回，再用大模型做结构化理解

当前对外输出已经压缩为统一格式：

```json
{
  "doc_id": "doc_001",
  "extractions": [
    {
      "raw_field": "合同金额",
      "value": "120万元",
      "source": "paragraph",
      "para_id": 3
    },
    {
      "raw_field": "项目负责人",
      "value": "张三",
      "source": "paragraph",
      "para_id": 4
    }
  ]
}
```

## 文件说明

- [extract_ai_1.0.py](/Users/st.peter/Documents/服务外包/DocFusion-AI/extract/extract_ai_1.0.py)
  抽取主脚本，直接读取 `data.json` 和 `field_synonyms.xlsx`

- [data.json](/Users/st.peter/Documents/服务外包/DocFusion-AI/extract/data.json)
  当前测试输入数据

- [field_synonyms.xlsx](/Users/st.peter/Documents/服务外包/DocFusion-AI/extract/field_synonyms.xlsx)
  字段同义词表，用于关键词候选定位

- [test.py](/Users/st.peter/Documents/服务外包/DocFusion-AI/extract/test.py)
  测试脚本，执行后会生成 `test_output.json`

- [hello.ipynb](/Users/st.peter/Documents/服务外包/DocFusion-AI/extract/hello.ipynb)
  notebook 版实验流程，适合调试候选定位和 LLM 提示词

## 抽取流程

### 1. 实体类字段抽取

实体字段包括：

- 项目名称
- 项目负责人
- 单位名称
- 甲方
- 乙方
- 联系人
- 联系电话
- 项目编号
- 合同编号
- 日期
- 金额

候选定位阶段包含三类来源：

- `paragraph`
  通过正则规则直接抽取明显格式字段

- `paragraph`
  通过同义词关键词在段落中截取候选片段

- `ner`
  通过轻量规则模拟实体识别，识别机构名、项目名等

结构化阶段会把候选发给通义千问，要求模型在候选中选择最可信的值，并返回标准 JSON。

### 2. 规则类字段抽取

规则字段当前包括：

- 适用条件
- 禁止约束
- 办理时限
- 申报材料

候选召回阶段会先按句子切分，再根据触发词召回候选句子。

结构化阶段会把候选发给通义千问，让模型输出规则语义。当前脚本内部保留了 `condition / subject / action / constraint` 的结构，但最终对外仍压成简洁结果。

## 大模型配置

当前脚本内部直接写入了通义千问兼容 OpenAI SDK 配置：

- `api_key`
- `base_url=https://dashscope.aliyuncs.com/compatible-mode/v1`
- `model=qwen-plus`

主脚本使用方式与下面示例一致：

```python
from openai import OpenAI

client = OpenAI(
    api_key="你的key",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
```

如果本地没有安装 `openai`，脚本会退回到 fallback 逻辑，不会真正发起模型请求。

## 依赖

至少需要安装：

```bash
pip install pandas openpyxl openai
```

说明：

- `pandas`
  用于读取字段同义词表

- `openpyxl`
  用于支持 `pandas.read_excel`

- `openai`
  用于调用通义千问兼容接口

## 运行主脚本

在项目根目录执行：

```bash
python3 extract/extract_ai_1.0.py
```

运行后会在终端打印抽取结果，结果格式为：

```json
{
  "doc_id": "...",
  "extractions": [
    {
      "raw_field": "...",
      "value": "...",
      "source": "paragraph",
      "para_id": 0
    }
  ]
}
```

## 运行测试

执行：

```bash
python3 -m unittest extract/test.py
```

测试会做两件事：

- 校验输出结果是否符合预期结构
- 自动生成结果文件 [test_output.json](/Users/st.peter/Documents/服务外包/DocFusion-AI/extract/test_output.json)

`test_output.json` 可直接用于查看当前 `data.json` 的抽取结果。

## 当前限制

- 当前测试依赖 `data.json` 这一份样本
- 规则类字段对外输出仍是简化结构，没有完整暴露内部语义槽位
- `tables` 还没有接入当前抽取流程
- 如果模型返回不规范 JSON，脚本会自动使用 fallback 结果

## 后续可扩展方向

- 把 `tables` 纳入候选定位
- 为不同文档类型配置不同字段集合
- 为规则字段输出更完整的结构化 JSON
- 增加数据库入库接口
- 增加多样本批量测试集
