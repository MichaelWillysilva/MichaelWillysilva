import pytest
import requests

from fontes.base import BaseSource


class NotFoundSession:
    def __init__(self):
        self.calls = 0

    def request(self, method, url, **kwargs):
        self.calls += 1
        response = requests.Response()
        response.status_code = 404
        response.url = url
        return response


def test_http_404_is_not_retried():
    source = BaseSource({"http": {"delay_seconds": 0, "retries": 3}})
    session = NotFoundSession()
    source.session = session

    with pytest.raises(requests.HTTPError):
        source._request_with_retry("https://example.org/missing")

    assert session.calls == 1
