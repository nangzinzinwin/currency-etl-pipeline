import sqlite3

import pandas as pd
import pytest
import requests
import requests_mock

from main import (
    fetch_currency_data,
    transform_currency_data,
    validate_currency_data,
    remove_old_data,
)


def test_fetch_currency_data_success():
    api_response = {
        "amount": 1.0,
        "base": "EUR",
        "date": "2026-08-14",
        "rates": {
            "USD": 1.17,
            "JPY": 173.50,
            "GBP": 0.86,
            "THB": 37.50
        }
    }

    url = (
        "https://api.frankfurter.app/"
        "latest?from=EUR&to=USD,JPY,GBP,THB"
    )

    # Mock the external API so the test does not make a real API request.
    with requests_mock.Mocker() as mock:
        mock.get(url, json=api_response, status_code=200)

        result = fetch_currency_data()

    assert result["base"] == "EUR"
    assert result["date"] == "2026-08-14"
    assert "USD" in result["rates"]
    assert "JPY" in result["rates"]


def test_fetch_currency_data_api_failure():
    url = (
        "https://api.frankfurter.app/"
        "latest?from=EUR&to=USD,JPY,GBP,THB"
    )

    # Simulate an API failure without depending on the real service.
    with requests_mock.Mocker() as mock:
        mock.get(url, status_code=500)

        with pytest.raises(requests.exceptions.HTTPError):
            fetch_currency_data()


def test_transform_currency_data():
    api_data = {
        "amount": 1.0,
        "base": "EUR",
        "date": "2026-08-14",
        "rates": {
            "USD": 1.17,
            "JPY": 173.50,
            "GBP": 0.86,
            "THB": 37.50
        }
    }

    df = transform_currency_data(api_data)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 4
    assert list(df.columns) == [
        "target_currency",
        "exchange_rate",
        "base_currency",
        "rate_date",
        "created_at"
    ]
    assert df["base_currency"].eq("EUR").all()
    assert df["rate_date"].eq("2026-08-14").all()


def test_transform_currency_data_missing_rates():
    api_data = {
        "amount": 1.0,
        "base": "EUR",
        "date": "2026-08-14",
        "rates": {}
    }

    df = transform_currency_data(api_data)

    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_validate_currency_data_valid():
    df = pd.DataFrame({
        "target_currency": ["USD", "JPY"],
        "exchange_rate": [1.17, 173.50],
        "base_currency": ["EUR", "EUR"],
        "rate_date": ["2026-08-14", "2026-08-14"]
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
        "base_currency": ["EUR"]
    })

    with pytest.raises(AssertionError):
        validate_currency_data(df)


def test_validate_currency_data_null_value():
    df = pd.DataFrame({
        "target_currency": ["USD"],
        "exchange_rate": [None],
        "base_currency": ["EUR"],
        "rate_date": ["2026-08-14"]
    })

    with pytest.raises(AssertionError):
        validate_currency_data(df)


def test_validate_currency_data_invalid_exchange_rate():
    df = pd.DataFrame({
        "target_currency": ["USD"],
        "exchange_rate": [0],
        "base_currency": ["EUR"],
        "rate_date": ["2026-08-14"]
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
            "2026-08-14"
        ],
        "created_at": [
            "2026-08-01 10:00:00",
            "2026-08-10 10:00:00",
            "2026-08-14 10:00:00"
        ]
    })

    # Use an in-memory database so the real exchange_rates.db is not modified.
    df.to_sql(
        "currency_rates",
        conn,
        if_exists="replace",
        index=False
    )

    remove_old_data(conn)

    result = pd.read_sql_query(
        "SELECT * FROM currency_rates",
        conn
    )

    assert "2026-08-01" not in result["rate_date"].values
    assert "2026-08-10" in result["rate_date"].values
    assert "2026-08-14" in result["rate_date"].values

    conn.close() 
