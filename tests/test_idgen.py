from libs.idgen import generate_id


def test_generate_id_uniqueness():
    ids = {generate_id() for _ in range(5)}
    assert len(ids) == 5
    for value in ids:
        assert isinstance(value, int)
        assert value > 0
