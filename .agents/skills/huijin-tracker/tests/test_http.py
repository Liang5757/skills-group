import unittest
from unittest.mock import patch
from urllib.error import URLError

from huijin_tracker.http import HttpClient, SourceFetchError


class HttpClientTests(unittest.TestCase):
    def test_failure_redacts_webhook_token_and_query(self):
        client = HttpClient(retries=0)
        url = "https://open.feishu.cn/open-apis/bot/v2/hook/secret-token?access_token=query-secret"

        with patch("huijin_tracker.http.urlopen", side_effect=URLError("offline")):
            with self.assertRaises(SourceFetchError) as raised:
                client.post_json(url, {"msg_type": "text"})

        message = str(raised.exception)
        self.assertIn("/hook/[redacted]", message)
        self.assertNotIn("secret-token", message)
        self.assertNotIn("query-secret", message)


if __name__ == "__main__":
    unittest.main()
