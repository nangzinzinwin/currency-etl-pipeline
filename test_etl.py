import sqlite3

import pandas as pd
import pytest
import requests_mock

from main import (
    fetch_currency_data,
    transform_currency_data,
    validate_currency_data,
    remove_old_data,
)


def test_fetch_currency_data_success():
    mock_response = {
        "amount": 1.0,
        "base": "EUR",
        "date": "2026-08-18",
        "rates": {
            "USD": 1.17,
            "JPY": 171.0,
            "GBP": 0.86,
            "THB": 37.0,
        },
    }

    with requests_mock.Mocker() as mock:
        mock.get(
            "https://api.frankfurter.app/latest?from=EUR&to=USD,JPY,GBP,THB",
            json=mock_response,
        )

        result = fetch_currency_data()

    assert result is not None
    assert result["base"] == "EUR"
    assert "rates" in result
    assert "USD" in result["rates"]
    assert "JPY" in result["rates"]
    assert "GBP" in result["rates"]
    assert "THB" in result["rates"]


def test_fetch_currency_data_failure():
    with requests_mock.Mocker() as mock:
        mock.get(
            "https://api.frankfurter.app/latest?from=EUR&to=USD,JPY,GBP,THB",
            status_code=500,
        )

        with pytest.raises(Exception):
            fetch_currency_data()


def test_transform_currency_data():
    data = {
        "amount": 1.0,
        "base": "EUR",
        "date": "2026-08-18",
        "rates": {
            "USD": 1.17,
            "JPY": 171.0,
            "GBP": 0.86,
            "THB": 37.0,
        },
    }

    result = transform_currency_data(data)

    assert isinstance(result, pd.DataFrame)
    assert not result.empty
    assert "target_currency" in result.columns
    assert "exchange_rate" in result.columns
    assert "base_currency" in result.columns
    assert "rate_date" in result.columns
    assert len(result) == 4


def test_transform_currency_data_missing_rates():
    data = {
        "amount": 1.0,
        "base": "EUR",
        "date": "2026-08-18",
        "rates": {},
    }

    result = transform_currency_data(data)

    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_validate_currency_data_valid():
    df = pd.DataFrame({
        "target_currency": ["USD", "JPY", "GBP", "THB"],
        "exchange_rate": [1.17, 171.0, 0.86, 37.0],
        "base_currency": ["EUR", "EUR", "EUR", "EUR"],
        "rate_date": [
            "2026-08-18",
            "2026-08-18",
            "2026-08-18",
            "2026-08-18",
        ],
    })

    validate_currency_data(df)


def test_validate_currency_data_empty():
    df = pd.DataFrame()

    with pytest.raises(AssertionError):
        validate_currency_data(df)


def test_validate_currency_data_missing_column():
    df = pd.DataFrame({
        "target_currency": ["USD"],
        "exchange_rate": [1.17],
        "base_currency": ["EUR"],
    })

    with pytest.raises(AssertionError):
        validate_currency_data(df)


def test_validate_currency_data_null_value():
    df = pd.DataFrame({
        "target_currency": ["USD", "JPY"],
        "exchange_rate": [1.17, None],
        "base_currency": ["EUR", "EUR"],
        "rate_date": ["2026-08-18", "2026-08-18"],
    })

    with pytest.raises(AssertionError):
        validate_currency_data(df)


def test_validate_currency_data_invalid_exchange_rate():
    df = pd.DataFrame({
        "target_currency": ["USD"],
        "exchange_rate": [-1.0],
        "base_currency": ["EUR"],
        "rate_date": ["2026-08-18"],
    })

    with pytest.raises(AssertionError):
        validate_currency_data(df)


def test_remove_old_data():
    conn = sqlite3.connect(":memory:")

    df = pd.DataFrame({
        "target_currency": ["USD", "USD", "USD"],
        "exchange_rate": [1.10, 1.15, 1.17],
        "base_currency": ["EUR", "EUR", "EUR"],
        "rate_date": [
            "2026-08-01",
            "2026-08-10",
            "2026-08-14",
        ],
        "created_at": [
            "2026-08-01 10:00:00",
            "2026-08-10 10:00:00",
            "2026-08-14 10:00:00",
        ],
    })

    # Use in-memory database for testing.
    df.to_sql(
        "currency_rates",
        conn,
        if_exists="replace",
        index=False,
    )

    remove_old_data(conn)

    result = pd.read_sql_query(
        "SELECT * FROM currency_rates",
        conn,
    )

    assert "2026-08-01" not in result["rate_date"].values
    assert "2026-08-10" not in result["rate_date"].values
    assert "2026-08-14" in result["rate_date"].values

    conn.close()
