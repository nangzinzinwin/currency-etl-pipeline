import requests
import pandas as pd
import sqlite3
from datetime import datetime


# Keep only the most recent 7 days of data
RETENTION_DAYS = 7


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


print("1. Fetching data from API...")

url = "https://api.frankfurter.app/latest?from=EUR&to=USD,JPY,GBP,THB"

# Add a User-Agent header
headers = {
    "User-Agent": "Mozilla/5.0"
}

try:
    # Send API request
    response = requests.get(
        url,
        headers=headers,
        timeout=10
    )

    if response.status_code == 200:

        # Convert response to JSON
        data = response.json()

        print("Raw JSON Data fetched successfully!")

        print("\n2. Transforming data...")

        # Extract API data
        base_currency = data['base']
        rate_date = data['date']
        rates_dict = data['rates']

        # Convert dictionary to Pandas DataFrame
        df = pd.DataFrame(
            list(rates_dict.items()),
            columns=['target_currency', 'exchange_rate']
        )

        # Add additional columns
        df['base_currency'] = base_currency
        df['rate_date'] = rate_date
        df['created_at'] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        print("Transformed DataFrame:")
        print(df)

        # Validate currency data
        validate_currency_data(df)

        print("\n3. Saving data to SQLite Database...")

        # Connect to SQLite database
        conn = sqlite3.connect("exchange_rates.db")

        # Save DataFrame to database
        df.to_sql(
            "currency_rates",
            conn,
            if_exists="append",
            index=False
        )

        print("Data successfully loaded into the database!")

        # Remove data older than the retention period
        conn.execute(f"""
            DELETE FROM currency_rates
            WHERE rate_date < date('now', '-{RETENTION_DAYS} days')
        """)

        conn.commit()

        print(
            f"Data older than {RETENTION_DAYS} days "
            "has been deleted."
        )

        print("\n--- Verifying Database Content ---")

        # Read data back from database
        result_df = pd.read_sql_query(
            "SELECT * FROM currency_rates",
            conn
        )

        print(result_df)

        # Close database connection
        conn.close()

    else:
        print(
            f"Failed to fetch data. "
            f"Status code: {response.status_code}"
        )

except requests.exceptions.RequestException as e:

    print(f"\nConnection Error occurred: {e}")
    print(
        "Please check your internet connection "
        "or try using a VPN."
        )
