from unittest import mock

from apps.messaging import typing as typing_mod


def test_start_and_get_typing_users():
    redis_mock = mock.Mock()
    redis_mock.hgetall.return_value = {b"1": b"100.0"}
    with mock.patch("apps.messaging.typing.get_redis_client", return_value=redis_mock), mock.patch(
        "apps.messaging.typing.time.time", return_value=102.0
    ):
        typing_mod.start_typing(1, 10)
        users = typing_mod.get_typing_users(10)
    assert users == [1]
    redis_mock.hset.assert_called()
    redis_mock.expire.assert_called()
