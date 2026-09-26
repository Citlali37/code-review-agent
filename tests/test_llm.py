import unittest

from code_review_agent.llm import LLMError, OpenAICompatibleClient


class OpenAICompatibleClientTests(unittest.TestCase):
    def test_extracts_assistant_message(self) -> None:
        message = OpenAICompatibleClient._extract_message(
            {
                "choices": [
                    {
                        "message": {
                            "content": "完成",
                            "reasoning_content": "internal-state",
                            "tool_calls": [{"id": "call-1", "function": {"name": "read_file"}}],
                        }
                    }
                ]
            }
        )
        self.assertEqual(message["content"], "完成")
        self.assertEqual(message["reasoning_content"], "internal-state")
        self.assertEqual(message["tool_calls"][0]["id"], "call-1")

    def test_rejects_malformed_response(self) -> None:
        with self.assertRaises(LLMError):
            OpenAICompatibleClient._extract_message({"choices": []})


if __name__ == "__main__":
    unittest.main()
