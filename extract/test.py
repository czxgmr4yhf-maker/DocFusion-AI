import importlib.util
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
MODULE_PATH = BASE_DIR / "extract_ai_1.0.py"
WORD_PATH = BASE_DIR / "word.json"
OUTPUT_PATH = BASE_DIR / "test_output.json"

SAMPLE_FILES = {
    "md": ROOT_DIR / "ok" / "output_json" / "md_2023年文化和旅游发展统计公报_md.json",
    "txt": ROOT_DIR / "ok" / "output_json" / "txt_2024年国民经济和社会发展统计公报（节选）_txt.json",
    "word": ROOT_DIR / "ok" / "output_json" / "word_2021年民政事业发展统计公报_docx.json",
    "xlsx": ROOT_DIR / "ok" / "output_json" / "Excel_糖尿病患者数据_xlsx.json",
}

REQUIRED_FIELDS = ["分类", "指标", "数值", "单位", "时间", "同比", "来源段落"]

BENCHMARKS = {
    "md": [
        {"indicator_contains": "公共图书馆总流通人次", "分类": "公共图书馆", "数值": "116061", "单位": "万人次", "时间": "2023年", "同比": "46.9"},
        {"indicator_contains": "全国旅行社营业收入", "数值": "4442.7", "单位": "亿元", "时间": "2023年"},
        {"indicator_contains": "星级饭店营业收入", "数值": "1609.0", "单位": "亿元", "时间": "2023年"},
        {"indicator_contains": "A级景区", "分类": "全国", "数值": "15721", "单位": "个", "时间": "2023年"},
        {"indicator_contains": "文化和旅游事业费", "分类": "全国", "数值": "1280.4", "单位": "亿元", "时间": "2023年", "同比": "6.5"},
        {"indicator_contains": "国内游客出游总花费", "数值": "4.9", "单位": "万亿元", "时间": "2023年", "同比": "140.3"},
    ],
    "txt": [
        {"indicator_contains": "国内生产总值", "数值": "1349084", "单位": "亿元", "时间": "2024年", "同比": "5.0"},
        {"indicator_contains": "东部地区生产总值", "分类": "东部地区", "数值": "702356", "单位": "亿元", "时间": "2024年", "同比": "5.0"},
        {"indicator_contains": "新能源汽车产量", "数值": "1316.8", "单位": "万辆", "时间": "2024年", "同比": "38.7"},
        {"indicator_contains": "粮食播种面积", "数值": "11932", "单位": "万公顷", "时间": "2024年"},
        {"indicator_contains": "粮食产量", "数值": "70650", "单位": "万吨", "时间": "2024年", "同比": "1.6"},
        {"indicator_contains": "规模以上工业企业利润", "数值": "74311", "单位": "亿元", "时间": "2024年", "同比": "3.3"},
    ],
    "word": [
        {"indicator_contains": "民政部门登记和管理的机构和设施共计", "分类": "全国", "数值": "238.0", "单位": "万个", "时间": "2021年"},
        {"indicator_contains": "职工总数", "数值": "1730.4", "单位": "万人", "时间": "2021年"},
        {"indicator_contains": "固定资产原价", "数值": "8610.0", "单位": "亿元", "时间": "2021年"},
        {"indicator_contains": "民政事业费支出", "分类": "全国", "数值": "4679.0", "单位": "亿元", "时间": "2021年"},
        {"indicator_contains": "省级行政区划单位", "数值": "34", "单位": "个", "时间": "2021年"},
        {"indicator_contains": "地级行政区划单位", "数值": "333", "单位": "个", "时间": "2021年"},
    ],
    "xlsx": [
        {"indicator_contains": "住院天数", "分类": "Caucasian", "数值": "1", "来源段落": 1},
        {"indicator_contains": "实验室检查次数", "分类": "Caucasian", "数值": "41", "来源段落": 1},
        {"indicator_contains": "药物数量", "分类": "Caucasian", "数值": "18", "来源段落": 2},
        {"indicator_contains": "诊断数量", "分类": "AfricanAmerican", "数值": "6", "来源段落": 3},
        {"indicator_contains": "住院次数", "分类": "AfricanAmerican", "数值": "1", "来源段落": 3},
        {"indicator_contains": "实验室检查次数", "分类": "Caucasian", "数值": "44", "来源段落": 4},
    ],
}


def load_module():
    spec = importlib.util.spec_from_file_location("extract_ai_1_0", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def normalize_text(text):
    if text is None:
        return ""
    return "".join(str(text).strip().replace("％", "%").split())


def validate_result(name, result):
    assert isinstance(result, dict), f"{name}: result 必须是 dict"
    assert "doc_id" in result, f"{name}: 缺少 doc_id"
    assert "doc_type" in result, f"{name}: 缺少 doc_type"
    assert "results" in result and isinstance(result["results"], list), f"{name}: results 必须是 list"
    assert result["results"], f"{name}: results 不能为空"

    for index, record in enumerate(result["results"]):
        for field in REQUIRED_FIELDS:
            assert field in record, f"{name}: record[{index}] 缺少字段 {field}"
            if field == "来源段落":
                assert isinstance(record[field], int), f"{name}: record[{index}] 来源段落必须是 int"
            else:
                assert record[field] not in {"", None}, f"{name}: record[{index}] 字段 {field} 不允许为空"


def field_matches(expected_value, actual_value):
    expected = normalize_text(expected_value)
    actual = normalize_text(actual_value)
    if not expected:
        return True
    if actual == expected:
        return True
    return actual.startswith(expected)


def benchmark_hit(records, expected):
    indicator_key = normalize_text(expected.get("indicator_contains", ""))
    for record in records:
        if indicator_key and indicator_key not in normalize_text(record.get("指标", "")):
            continue
        matched = True
        for key, value in expected.items():
            if key == "indicator_contains":
                continue
            if key == "来源段落":
                matched = record.get(key) == value
            else:
                matched = field_matches(value, record.get(key, ""))
            if not matched:
                break
        if matched:
            return True, record
    return False, None


def main():
    module = load_module()
    word_config = json.loads(WORD_PATH.read_text(encoding="utf-8"))

    batch_result = {}
    total_checks = 0
    total_hits = 0

    for name, sample_path in SAMPLE_FILES.items():
        data = json.loads(sample_path.read_text(encoding="utf-8"))
        result = module.extract(data, word_config=word_config)
        validate_result(name, result)

        checks = []
        hits = 0
        for expected in BENCHMARKS[name]:
            ok, matched_record = benchmark_hit(result["results"], expected)
            hits += int(ok)
            checks.append(
                {
                    "expected": expected,
                    "matched": ok,
                    "matched_record": matched_record,
                }
            )

        total_checks += len(BENCHMARKS[name])
        total_hits += hits
        accuracy = hits / len(BENCHMARKS[name])

        batch_result[name] = {
            "doc_id": result["doc_id"],
            "doc_type": result["doc_type"],
            "result_count": len(result["results"]),
            "accuracy": round(accuracy, 4),
            "hits": hits,
            "total": len(BENCHMARKS[name]),
            "preview": result["results"][:5],
            "checks": checks,
        }
        print(f"[{name}] doc_type={result['doc_type']} result_count={len(result['results'])} accuracy={accuracy:.2%} ({hits}/{len(BENCHMARKS[name])})")

    overall_accuracy = total_hits / total_checks if total_checks else 0.0
    batch_result["summary"] = {
        "overall_accuracy": round(overall_accuracy, 4),
        "hits": total_hits,
        "total": total_checks,
    }

    OUTPUT_PATH.write_text(
        json.dumps(batch_result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n总体准确率: {overall_accuracy:.2%} ({total_hits}/{total_checks})")
    print(f"已写入: {OUTPUT_PATH}")

    assert overall_accuracy >= 0.8, f"总体准确率未达到 80%，当前为 {overall_accuracy:.2%}"


if __name__ == "__main__":
    main()
