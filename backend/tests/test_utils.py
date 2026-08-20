import pytest

from utils import bool_of_str


@pytest.mark.parametrize("raw_value", ["true", " True ", "TRUE"])
def test_bool_of_str_accepts_true_variants(raw_value):
    assert bool_of_str(raw_value) is True


@pytest.mark.parametrize("raw_value", ["false", " False ", "FALSE"])
def test_bool_of_str_accepts_false_variants(raw_value):
    assert bool_of_str(raw_value) is False


@pytest.mark.parametrize("raw_value", ["", "yes", "0", "truthy"])
def test_bool_of_str_rejects_non_boolean_strings(raw_value):
    with pytest.raises(ValueError, match="Invalid boolean string"):
        bool_of_str(raw_value)
