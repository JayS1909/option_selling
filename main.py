import config
from dhanhq import dhanhq
import pandas as pd

print("--- Starting Final Name Debug Script ---")

try:
    dhan = dhanhq(config.DHAN_CLIENT_ID, config.DHAN_ACCESS_TOKEN)
    print("Dhan API client initialized successfully.")

    print("\nFetching security list...")
    df = dhan.fetch_security_list()
    print("Security list fetched successfully.")

    print("\n--- Unique Values in 'SEM_INSTRUMENT_NAME' for NSE Exchange ---")
    # This uses the CORRECT exchange filter ('NSE')
    fno_instruments = df[df['SEM_EXM_EXCH_ID'] == 'NSE']
    print(fno_instruments['SEM_INSTRUMENT_NAME'].unique())
    print("------------------------------------------------------------\n")

except Exception as e:
    print(f"An error occurred: {e}")

print("--- Debug Script Finished ---")
