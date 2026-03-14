import importlib.util
import json
import unittest
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


class ExtractionScriptTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        cls.module.build_client = lambda: None
        cls.result = cls.module.extract(cls.data)
        OUTPUT_PATH.write_text(
            json.dumps(cls.result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def test_extract_returns_expected_top_level_shape(self):
        self.assertIsInstance(self.result, dict)
        self.assertEqual(self.result["doc_id"], self.data["doc_id"])
        self.assertIn("extractions", self.result)
        self.assertIsInstance(self.result["extractions"], list)

    def test_each_extraction_matches_simplified_schema(self):
        for item in self.result["extractions"]:
            self.assertIsInstance(item, dict)
            self.assertEqual(set(item.keys()), {"raw_field", "value", "source", "para_id"})
            self.assertIsInstance(item["raw_field"], str)
            self.assertTrue(item["raw_field"])
            self.assertIn(item["source"], {"paragraph", "ner", "sentence", "llm"})
            self.assertIsInstance(item["para_id"], int)

    def test_result_contains_at_least_one_extraction(self):
        self.assertGreater(len(self.result["extractions"]), 0)

    def test_output_file_is_written(self):
        self.assertTrue(OUTPUT_PATH.exists())
        written = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(written["doc_id"], self.result["doc_id"])
        self.assertEqual(written["extractions"], self.result["extractions"])


if __name__ == "__main__":
    unittest.main()
