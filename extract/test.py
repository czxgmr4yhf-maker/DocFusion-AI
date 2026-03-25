import importlib.util
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
MODULE_PATH = BASE_DIR / "extract_ai_1.0.py"
DATA_PATH = BASE_DIR / "data.json"
OUTPUT_PATH = BASE_DIR / "test_output.json"


def load_module():
    spec = importlib.util.spec_from_file_location("extract_ai_1_0", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main():
    module = load_module()
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    result = module.extract(data)
    OUTPUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n已写入: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
