import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as backend_app


class ReportEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = backend_app.app.test_client()
        self.client.testing = True

    def test_report_returns_parsed_json_without_llm_advice(self) -> None:
        fake_html = "<html><body>report</body></html>"
        expected_parsed = {"max_loss_turn": {"kyoku": "E1", "turn": 1}}
        mock_advice = "Mocked LLM advice"

        with patch("app.interactakochan.call_report", return_value=fake_html) as mock_call_report, patch(
            "app.extract.extract_report", return_value=expected_parsed
        ) as mock_extract, patch(
            "app.interactllm._generate_advice", return_value=mock_advice
        ) as mock_generate_advice:
            response = self.client.post("/report?seat=0&source_type=url&url=https://example.com")

        self.assertEqual(response.status_code, 200)
        expected_response = expected_parsed.copy()
        expected_response["llm_advice"] = mock_advice
        self.assertEqual(response.get_json(), expected_response)
        mock_call_report.assert_called_once()
        mock_extract.assert_called_once()
        mock_generate_advice.assert_called_once()



if __name__ == "__main__":
    unittest.main()
