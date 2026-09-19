import pytest
from src.utils import normalize_card

def test_normalize_card():
    assert normalize_card("10214916") == "10214916"
    assert normalize_card("0563863044") == "10214916"
    assert normalize_card("563863044") == "10214916"