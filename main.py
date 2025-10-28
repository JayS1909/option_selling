import config
import pandas as pd
from datetime import datetime, date, time
import time as os_time
import os
import xlwings as xw

# We assume the user has placed the custom Dhan_Tradehull.py library
# in the same directory as this script.
try:
    from Dhan_Tradehull import Tradehull
except ImportError:
    print("FATAL ERROR: The 'Dhan_Tradehull_V2' library is not installed.")
    print("Please make sure the library file is in the same directory or installed in your Python environment.")
    exit()

def initialize_tradehull():
    """Initializes the Tradehull object."""
    try:
        tsl = Tradehull(config.DHAN_CLIENT_ID, config.DHAN_ACCESS_TOKEN)
        print("Tradehull client initialized successfully.")
        return tsl
    except Exception as e:
        print(f"Error initializing Tradehull client: {e}")
        return None

def run_live_paper_trade(tsl):
    """
    Executes the 9:20 AM strategy to fetch live prices and log them.
    This is a LIVE PAPER TRADING tool.
    """
    print(f"\n--- Running Live Paper Trade for {date.today().strftime('%Y-%m-%d')} ---")

    # --- Get ATM and OTM strikes using the library's functions ---
    # The Expiry=0 argument fetches the nearest weekly expiry automatically.
    print("Fetching option strikes...")
    try:
        short_ce_symbol, short_pe_symbol, short_ce_strike, short_pe_strike = tsl.OTM_Strike_Selection(
            Underlying=config.TRADING_SYMBOL, Expiry=0, OTM_count=config.SHORT_OTM_STEPS
        )
        hedge_ce_symbol, hedge_pe_symbol, hedge_ce_strike, hedge_pe_strike = tsl.OTM_Strike_Selection(
            Underlying=config.TRADING_SYMBOL, Expiry=0, OTM_count=config.HEDGE_OTM_STEPS
        )
    except Exception as e:
        print(f"Error during strike selection: {e}")
        print("This might be due to incorrect credentials or being outside market hours.")
        return

    if not all([short_ce_symbol, short_pe_symbol, hedge_ce_symbol, hedge_pe_symbol]):
        print("Could not retrieve all necessary option symbols. Exiting.")
        return

    print(f"Short Strikes -> CE: {short_ce_strike} ({short_ce_symbol}), PE: {short_pe_strike} ({short_pe_symbol})")
    print(f"Hedge Strikes -> CE: {hedge_ce_strike} ({hedge_ce_symbol}), PE: {hedge_pe_strike} ({hedge_pe_symbol})")

    # --- Fetch Live Prices ---
    print("Fetching live prices for all option legs...")
    option_symbols = [short_ce_symbol, short_pe_symbol, hedge_ce_symbol, hedge_pe_symbol]

    try:
        ltp_data = tsl.get_ltp_data(names=option_symbols)
        if not all(symbol in ltp_data for symbol in option_symbols):
            print("Could not fetch LTP for all symbols.")
            return
    except Exception as e:
        print(f"Error fetching LTP data: {e}")
        return

    short_ce_premium = ltp_data.get(short_ce_symbol, 0)
    short_pe_premium = ltp_data.get(short_pe_symbol, 0)
    hedge_ce_premium = ltp_data.get(hedge_ce_symbol, 0)
    hedge_pe_premium = ltp_data.get(hedge_pe_symbol, 0)

    # --- Log the Data ---
    trade_log = {
        'Date': date.today().strftime('%Y-%m-%d'),
        'Timestamp': datetime.now().strftime('%H:%M:%S'),
        'Underlying': config.TRADING_SYMBOL,
        'Short CE Strike': short_ce_strike, 'Short CE Premium': short_ce_premium,
        'Hedge CE Strike': hedge_ce_strike, 'Hedge CE Premium': hedge_ce_premium,
        'Short PE Strike': short_pe_strike, 'Short PE Premium': short_pe_premium,
        'Hedge PE Strike': hedge_pe_strike, 'Hedge PE Premium': hedge_pe_premium,
        'Net Credit': (short_ce_premium + short_pe_premium) - (hedge_ce_premium + hedge_pe_premium)
    }

    print("\n--- Live Trade Data Captured ---")
    print(pd.Series(trade_log))
    export_to_excel(trade_log)

def export_to_excel(trade_log):
    """Exports the trade log dictionary to an Excel file."""
    if not trade_log: return
    new_df = pd.DataFrame([trade_log])
    filename = config.EXCEL_FILE_NAME

    columns = list(trade_log.keys())
    new_df = new_df[columns]

    try:
        if os.path.isfile(filename):
            existing_df = pd.read_excel(filename)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df
        combined_df.to_excel(filename, index=False, sheet_name='LiveTradeLog')
        print(f"\nSuccessfully exported trade data to {filename}")
    except Exception as e:
        print(f"Error exporting to Excel: {e}")

def main():
    """Main function to run the script."""
    print("--- 9:20 Hedged OTM Strategy - Live Paper Trading Tool ---")

    # Optional: Wait until 9:20 AM to run
    entry_time = time(9, 20)
    while datetime.now().time() < entry_time:
        print(f"Waiting for {entry_time}... Current time is {datetime.now().strftime('%H:%M:%S')}", end="\r")
        os_time.sleep(1)

    tsl = initialize_tradehull()
    if tsl:
        run_live_paper_trade(tsl)

if __name__ == "__main__":
    main()
