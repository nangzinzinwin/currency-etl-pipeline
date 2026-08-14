import requests
import pandas as pd
import sqlite3
from datetime import datetime


# Keep only the most recent 7 days of data
RETENTION_DAYS = 7


def fetch_currency_data():
    """
    Fetch currency exchange rate data from Frankfurter API.
    """

    url = "https://api.frankfurter.app/latest?from=EUR&to=USD,JPY,GBP,THB"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=10
    )

    response.raise_for_status()

    return response.json()


def transform_currency_data(data: dict) -> pd.DataFrame:
    """
    Transform API JSON data into a Pandas DataFrame.
    """

    base_currency = data['base']
    rate_date = data['date']
    rates_dict = data['rates']

    df = pd.DataFrame(
        list(rates_dict.items()),
        columns=['target_currency', 'exchange_rate']
    )

    df['base_currency'] = base_currency
    df['rate_date'] = rate_date
    df['created_at'] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    return df


def validate_currency_data(df: pd.DataFrame):
    """
    Validate currency exchange rate data.
    """

    # 1. Check if DataFrame is empty
    assert not df.empty, "Error: DataFrame is empty!"

    # 2. Check for required columns
    required_columns = [
        'target_currency',
        'exchange_rate',
        'base_currency',
        'rate_date'
    ]

    for col in required_columns:
        assert col in df.columns, \
            f"Error: Missing required column '{col}'!"

    # 3. Check for missing values
    assert not df.isnull().values.any(), \
        "Error: Data contains missing values!"

    # 4. Check if exchange rates are greater than zero
    assert (df['exchange_rate'] > 0).all(), \
        "Error: Exchange rates must be greater than zero!"

    print("All data validation checks passed successfully!")


def save_to_database(df: pd.DataFrame):
    """
    Save currency data to SQLite database.
    """

    conn = sqlite3.connect("exchange_rates.db")

    df.to_sql(
        "currency_rates",
        conn,
        if_exists="append",
        index=False
    )

    conn.commit()

    print("Data successfully loaded into the database!")

    return conn


def remove_old_data(conn):
    """
    Remove data older than the retention period.
    """

    conn.execute(f"""
        DELETE FROM currency_rates
        WHERE rate_date < date('now', '-{RETENTION_DAYS} days')
    """)

    conn.commit()

    print(
        f"Data older than {RETENTION_DAYS} days "
        "has been deleted."
    )


def verify_database(conn):
    """
    Read and display the current database content.
    """

    print("\n--- Verifying Database Content ---")

    result_df = pd.read_sql_query(
        "SELECT * FROM currency_rates",
        conn
    )

    print(result_df)


def main():
    """
    Run the Currency ETL Pipeline.
    """

    print("1. Fetching data from API...")

    try:
        # Extract
        data = fetch_currency_data()

        print("Raw JSON Data fetched successfully!")

        # Transform
        print("\n2. Transforming data...")

        df = transform_currency_data(data)

        print("Transformed DataFrame:")
        print(df)

        # Validate
        validate_currency_data(df)

        # Load
        print("\n3. Saving data to SQLite Database...")

        conn = save_to_database(df)

        # Retention
        remove_old_data(conn)

        # Verify
        verify_database(conn)

        # Close database connection
        conn.close()

    except requests.exceptions.RequestException as e:

        print(f"\nConnection Error occurred: {e}")

        print(
            "Please check your internet connection "
            "or try using a VPN."
        )


if __name__ == "__main__":
    main() 
