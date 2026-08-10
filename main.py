import requests
import pandas as pd
import sqlite3
from datetime import datetime

print("1. Fetching data from API...")

url = "https://api.frankfurter.app/latest?from=EUR&to=USD,JPY,GBP,THB"

# Adding a User-Agent header to prevent the server from blocking the request
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

try:
    # Pass the headers and set a timeout of 10 seconds
    response = requests.get(url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        print("Raw JSON Data fetched successfully!")
        
        print("\n2. Transforming data...")
        
        base_currency = data['base']
        rate_date = data['date']
        rates_dict = data['rates']
        
        # Convert dictionary to Pandas DataFrame
        df = pd.DataFrame(list(rates_dict.items()), columns=['target_currency', 'exchange_rate'])
        
        # Add new columns
        df['base_currency'] = base_currency
        df['rate_date'] = rate_date
        df['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print("Transformed DataFrame:")
        print(df)
        
        print("\n3. Saving data to SQLite Database...")
        
        # Connect to database and save
        conn = sqlite3.connect("exchange_rates.db")
        df.to_sql("currency_rates", conn, if_exists="append", index=False)
        
        print("Data successfully loaded into the database!")
        
        print("\n--- Verifying Database Content ---")
        result_df = pd.read_sql_query("SELECT * FROM currency_rates", conn)
        print(result_df)
        
        conn.close()
        
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")

except requests.exceptions.RequestException as e:
    # Catch any network or connection errors and print a clear message
    print(f"\nConnection Error occurred: {e}")
    print("Please check your internet connection or try using a VPN.")

