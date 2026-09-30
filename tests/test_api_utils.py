import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests

from browsergym.workarena.api import utils


@pytest.fixture
def instance():
    return SimpleNamespace(snow_url="https://example.invalid", snow_credentials=("user", "pass"))


def make_response(status_code, content):
    response = requests.Response()
    response.status_code = status_code
    response.url = "https://example.invalid/api/now/table/incident"
    response._content = content
    return response


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "DELETE"])
@pytest.mark.parametrize(
    "status_code, content",
    [(401, b'{"error": {"message": "Unauthorized"}}'), (503, b"<html>Unavailable</html>")],
)
def test_table_api_raises_http_error_before_decoding(
    monkeypatch, instance, method, status_code, content
):
    response = make_response(status_code, content)
    decode = Mock(wraps=response.json)
    monkeypatch.setattr(response, "json", decode)
    request = Mock(return_value=response)
    sleep = Mock()
    monkeypatch.setattr(utils.requests, "request", request)
    monkeypatch.setattr(utils, "sleep", sleep)

    with pytest.raises(requests.HTTPError) as exc_info:
        utils.table_api_call(instance, table="incident", method=method)

    assert exc_info.value.response is response
    decode.assert_not_called()
    sleep.assert_not_called()
    assert request.call_count == 1


def test_table_api_successful_post_still_waits_for_record(monkeypatch, instance):
    created = {"result": {"sys_id": "record-123"}}
    request = Mock(
        side_effect=[
            make_response(201, json.dumps(created).encode()),
            make_response(200, b'{"result": [{"sys_id": "record-123"}]}'),
        ]
    )
    monkeypatch.setattr(utils.requests, "request", request)
    monkeypatch.setattr(utils, "sleep", Mock())

    result = utils.table_api_call(instance, table="incident", method="POST")

    assert result == created
    assert request.call_count == 2
    assert request.call_args_list[0].kwargs["method"] == "POST"
    assert request.call_args_list[1].kwargs["method"] == "GET"
    assert request.call_args_list[1].kwargs["params"] == {"sysparm_query": "sys_id=record-123"}
