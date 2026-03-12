不同类型文档在解析后都需要转化为统一的JSON数据结构，以便后续模块使用，标题、上下标等不用考虑了，最后JSON文件就用"A23 竞赛执行方案.pdf"里面的4个字段
"doc_id"、"paragraphs"、"tables"、"raw_text"：
	doc_id‌：
	‌含义‌：文档ID。这是一个唯一标识符，用于区分不同的文档。反映文档的原始位置和类型，便于后续处理与追溯。格式： "[子目录路径_]原文件名_扩展名"，其中子目录路径的分隔符替换为下划线。
	‌paragraphs‌：
	‌含义‌：段落数组。这个字段包含文档中所有段落的列表。每个段落通常是文本的一部分，可能包含一个或多个句子。
	‌tables‌：
	含义‌：表格数组。这个字段包含文档中所有表格的列表。每个表格可能包含行和列的数据，通常用于表示结构化信息，如统计数据、产品目录等。
	‌raw_text‌：
	含义‌：原始文本。这个字段包含文档的完整、未经处理的文本内容。这可以用于原始数据的存储或在某些情况下作为其他字段（如paragraphs和tables）的备用或补充。


requirements.txt和environment.yml都已经导出，其实文档解析部分环境配置就这三行：（以conda为例）
	conda create -n rag python=3.10
	conda activate rag
	pip install python-docx openpyxl

list了一下，这两个包版本如下：
python-docx                1.2.0
openpyxl                   3.1.5


用法：
命令行里
python doc_parser.py /path/to/your/documents -o /path/to/output
•input_dir：必选，包含待解析文档的目录。
•-o, --output_dir：可选，指定输出目录；默认在输入目录下创建 output_json 文件夹。
例如：命令行运行
python doc_parser.py test_docs -o output_json


目前测试集里一个docx解析失败，一个xlsx解析警告，数据未能成功解析。下一步继续提高解析成功率和准确率。

改进4 数据清洗
•新增 _clean_text 方法
	移除控制字符（\x00-\x08\x0b\x0c\x0e-\x1f\x7f），避免不可见符号干扰。
	将内部的连续空白（空格、制表符、换行等）合并为单个空格，使文本规整。
	去除首尾空白。
•清洗段落和表格
	_clean_paragraphs 和 _clean_tables 分别对段落列表和表格数据递归应用清洗。
•清洗后自动过滤掉完全空白的段落或行（可选，可根据实际需求调整）。

改进3 文件夹下子目录遍历问题，同时存放doc_id字段
批量解析指定目录及其所有子目录下的支持文档，并将每个文档的解析结果保存为 JSON 文件。输出文件名格式：[子目录路径_]原文件名_扩展名.json（子目录路径中的分隔符替换为下划线）
•递归遍历：使用 input_dir.rglob('*') 扫描所有子目录。
•文件名包含路径：通过 rel_path.parts 获取目录层级，将目录部分用下划线连接，与原文件名和扩展名组合，确保唯一性。

改进2 文件名问题
•输出文件名生成：在 batch_parse 中，输出文件名修改为 f"{file_path.stem}_{ext[1:]}.json"，例如 a.docx → a_docx.json，a.txt → a_txt.json，确保同名的不同格式文件都能保留。

改进1 编码问题
•_read_text_file 方法：新增一个通用文本读取方法，尝试 utf-8、gbk、gb2312、utf-16、latin-1 五种编码，避免因编码不兼容导致的解码错误。_parse_markdown 和 _parse_txt 都使用该方法读取文件内容。