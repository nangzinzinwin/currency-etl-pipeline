import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import requests_mock

from main import (
    fetch_currency_data,
    transform_currency_data,
    validate_currency_data,
    remove_old_data
)


def test_fetch_currency_data_success():
    with requests_mock.Mocker() as mock:
        mock.get(
            "https://api.frankfurter.app/latest?from=EUR&to=USD,JPY,GBP,THB",
            json={
                "amount": 1,
                "base": "EUR",
                "date": "2026-08-18",
                "rates": {
                    "USD": 1.17,
                    "JPY": 171.0,
                    "GBP": 0.86,
                    "THB": 37.0
                }
            }
        )

        result = fetch_currency_data()

        assert result["base"] == "EUR"
        assert "rates" in result
        assert result["rates"]["USD"] == 1.17


def test_fetch_currency_data_failure():
    with requests_mock.Mocker() as mock:
        mock.get(
            "https://api.frankfurter.app/latest?from=EUR&to=USD,JPY,GBP,THB",
            status_code=500
        )

        try:
            fetch_currency_data()
            assert False
        except Exception:
            assert True


def test_transform_currency_data():
    data = {
        "amount": 1,
        "base": "EUR",
        "date": "2026-08-18",
        "rates": {
            "USD": 1.17,
            "JPY": 171.0,
            "GBP": 0.86,
            "THB": 37.0
        }
    }

    result = transform_currency_data(data)

    assert len(result) == 4
    assert "target_currency" in result.columns
    assert "exchange_rate" in result.columns
    assert "base_currency" in result.columns
    assert "rate_date" in result.columns


def test_transform_currency_data_missing_rates():
    data = {
        "amount": 1,
        "base": "EUR",
        "date": "2026-08-18"
    }

    try:
        transform_currency_data(data)
        assert False
    except Exception:
        assert True


def test_validate_currency_data_valid():
    df = pd.DataFrame({
        "target_currency": ["USD", "JPY", "GBP", "THB"],
        "exchange_rate": [1.17, 171.0, 0.86, 37.0],
        "base_currency": ["EUR", "EUR", "EUR", "EUR"],
        "rate_date": [
            "2026-08-18",
            "2026-08-18",
            "2026-08-18",
            "2026-08-18"
        ]
    })

    result = validate_currency_data(df)

    assert result is None


def test_validate_currency_data_empty():
    df = pd.DataFrame()

    try:
        validate_currency_data(df)
        assert False
    except (AssertionError, ValueError):
        assert True


def test_validate_currency_data_missing_column():
    df = pd.DataFrame({
        "target_currency": ["USD"],
        "exchange_rate": [1.17],
        "base_currency": ["EUR"]
    })

    try:
        validate_currency_data(df)
        assert False
    except (AssertionError, ValueError):
        assert True


def test_validate_currency_data_null_value():
    df = pd.DataFrame({
        "target_currency": ["USD"],
        "exchange_rate": [None],
        "base_currency": ["EUR"],
        "rate_date": ["2026-08-18"]
    })

    try:
        validate_currency_data(df)
        assert False
    except (AssertionError, ValueError):
        assert True


def test_validate_currency_data_invalid_exchange_rate():
    df = pd.DataFrame({
        "target_currency": ["USD"],
        "exchange_rate": [-1.0],
        "base_currency": ["EUR"],
        "rate_date": ["2026-08-18"]
    })

    try:
        validate_currency_data(df)
        assert False
    except (AssertionError, ValueError):
        assert True


def test_remove_old_data():
    conn = sqlite3.connect(":memory:")

    today = datetime.now()

    old_date = (today - timedelta(days=8)).strftime("%Y-%m-%d")
    recent_date = (today - timedelta(days=2)).strftime("%Y-%m-%d")

    df = pd.DataFrame({
        "target_currency": ["USD", "USD"],
        "exchange_rate": [1.10, 1.15],
        "base_currency": ["EUR", "EUR"],
        "rate_date": [old_date, recent_date],
        "created_at": [
            (today - timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S"),
            (today - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        ]
    })

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

    assert old_date not in result["rate_date"].values
    assert recent_date in result["rate_date"].values

    conn.close()
