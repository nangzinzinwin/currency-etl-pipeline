# Currency ETL Pipeline

[![Currency ETL Pipeline](https://github.com/nangzinzinwin/currency-etl-pipeline/actions/workflows/etl.yml/badge.svg)](https://github.com/nangzinzinwin/currency-etl-pipeline/actions/workflows/etl.yml)

Automated ETL pipeline to fetch EUR exchange rates, validate data quality, and store the last 7 days of records in SQLite using GitHub Actions.

## Key Functions
- Fetch rates from Frankfurter API
- Perform data validation (check schema, missing values, rate validity)
- Save to SQLite and retain 7-day historical window
- Scheduled daily automation via GitHub Actions
