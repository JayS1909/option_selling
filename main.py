import config
import pandas as pd
from datetime import datetime, date, timedelta
from dhanhq import dhanhq

# --- Dhan API Initialization ---
try:
    dhan = dhanhq(config.DHAN_CLIENT_ID, config.DHAN_ACCESS_TOKEN)
    print("Dhan API client initialized successfully.")
except Exception as e:
    print(f"Error initializing Dhan API client: {e}")
    exit()

# --- Placeholder Functions for API Interaction ---

def get_security_id(symbol, exchange='NSE_FNO'):
    """Fetches the security ID for a given symbol."""
    # For major indices like BANKNIFTY, it's faster and more reliable to use their known IDs.
    if symbol == "BANKNIFTY":
        return 26009  # Known Security ID for BANKNIFTY index (underlying for options)

    # Fallback for other symbols. Note: Fetching the entire scrip master can be slow.
    # The correct method is `get_scrip_master()`, not `get_tradeable_instrument()`.
    print(f"Attempting to find security ID for {symbol} from scrip master (this may be slow)...")
    try:
        # Corrected API call
        instruments = dhan.get_scrip_master()
        df = pd.DataFrame(instruments['data'])

        # Find a suitable instrument for the symbol. This logic may need refinement
        # depending on whether you need a future or an index.
        fno_security = df[(df['SEM_INSTRUMENT_NAME'] == symbol) & (df['SEM_EXM_EXCH_ID'] == 'NSE_FNO')]
        if not fno_security.empty:
            # This returns the first match, which might not always be the intended one.
            # For the purpose of this script, we primarily care about the BANKNIFTY case above.
            return fno_security.iloc[0]['SEM_SMST_SECURITY_ID']

    except Exception as e:
        print(f"Could not fetch from scrip master or find symbol. Error: {e}")

    print(f"Security ID for {symbol} not found.")
    return None


def get_nearest_weekly_expiry(symbol_id):
    """Finds the nearest weekly expiry date."""
    # Fetch expiry dates for the given security ID
    expiries = dhan.option_chain(
        security_id=str(symbol_id),
        exchange_segment='NSE_FNO',
        instrument_type='OPTIDX'
    )['data']['expiry_dates']

    today = date.today()

    # Convert expiry strings to date objects
    expiry_dates = [datetime.strptime(exp, '%d-%m-%Y').date() for exp in expiries]

    # Filter for future expiries
    future_expiries = sorted([exp for exp in expiry_dates if exp >= today])

    # Find the nearest Thursday (or Wednesday if Thursday is a holiday)
    # The first one in the sorted list is usually the nearest weekly expiry.
    if future_expiries:
        return future_expiries[0].strftime('%d-%m-%Y')

    return None

def get_option_chain(security_id, expiry_date):
    """Fetches the option chain for a given security ID and expiry."""
    try:
        option_chain = dhan.option_chain(
            security_id=str(security_id),
            exchange_segment='NSE_FNO',
            instrument_type='OPTIDX',
            expiry_date=expiry_date
        )['data']
        return option_chain['option_chains']
    except Exception as e:
        print(f"Error fetching option chain: {e}")
        return None

def get_historical_data(instrument_id, from_date, to_date, exchange='NSE_FNO'):
    """Fetches historical intraday 1-minute data."""
    try:
        data = dhan.get_historical_intraday_data(
            security_id=str(instrument_id),
            exchange_segment=exchange,
            instrument_type='EQUITY', # 'INDEX' or 'OPTIDX' might be needed
            from_date=from_date,
            to_date=to_date
        )
        if data['status'] == 'success':
            return pd.DataFrame(data['data'])
    except Exception as e:
        print(f"Error fetching historical data for {instrument_id}: {e}")
    return pd.DataFrame()

def get_price_at_time(instrument_id, target_dt, exchange='NSE_FNO', instrument_type='OPTIDX'):
    """Gets the closing price of an instrument at a specific time."""
    from_date = to_date = target_dt.strftime('%Y-%m-%d')

    # For index spot price, the instrument type is 'INDEX'
    if instrument_type == 'INDEX':
        instrument_type = 'INDICES' # Dhan API uses 'INDICES' for cash market index
        exchange = 'NSE_INDEX'

    try:
        hist_data = dhan.get_historical_intraday_data(
            security_id=str(instrument_id),
            exchange_segment=exchange,
            instrument_type=instrument_type,
            from_date=from_date,
            to_date=to_date
        )

        if hist_data['status'] == 'success' and 'data' in hist_data and hist_data['data']:
            df = pd.DataFrame(hist_data['data'])
            df['datetime'] = pd.to_datetime(df['start_Time'], unit='s')

            # Find the candle corresponding to the target time
            target_candle = df[df['datetime'] == target_dt]
            if not target_candle.empty:
                return target_candle.iloc[0]['close']
            else:
                print(f"No data found at exact time {target_dt} for {instrument_id}. Using nearest available.")
                # Fallback to nearest if exact time not found
                time_diff = (df['datetime'] - target_dt).abs()
                nearest_idx = time_diff.idxmin()
                return df.loc[nearest_idx]['close']

    except Exception as e:
        print(f"Error fetching price at time for {instrument_id}: {e}")

    return 0.0

def get_intraday_price_history(instrument_id, sim_date, exchange='NSE_FNO', instrument_type='OPTIDX'):
    """Gets the intraday price history (open, high, low, close) for an instrument."""
    from_date = to_date = sim_date.strftime('%Y-%m-%d')
    try:
        hist_data = dhan.get_historical_intraday_data(
            security_id=str(instrument_id),
            exchange_segment=exchange,
            instrument_type=instrument_type,
            from_date=from_date,
            to_date=to_date
        )
        if hist_data['status'] == 'success' and 'data' in hist_data and hist_data['data']:
            df = pd.DataFrame(hist_data['data'])
            df['datetime'] = pd.to_datetime(df['start_Time'], unit='s')
            return df[['datetime', 'high']]
    except Exception as e:
        print(f"Error fetching intraday history for {instrument_id}: {e}")
    return pd.DataFrame()


def find_option_instrument(option_chain, strike, option_type):
    """Finds the instrument ID for a given strike and type from the option chain."""
    for option in option_chain:
        if option['strike_price'] == strike:
            if option_type == 'CE' and option['ce_tradingsymbol']:
                return option['ce_dhan_instrument_id']
            elif option_type == 'PE' and option['pe_tradingsymbol']:
                return option['pe_dhan_instrument_id']
    return None

def run_simulation(sim_date: date):
    """Runs the entire simulation for a given date."""
    print(f"\n--- Running Simulation for {sim_date.strftime('%Y-%m-%d')} ---")

    # --- Setup ---
    security_id = get_security_id(config.TRADING_SYMBOL)
    if not security_id:
        return None

    expiry_str = get_nearest_weekly_expiry(security_id)
    if not expiry_str:
        print("Could not find expiry date.")
        return None

    option_chain = get_option_chain(security_id, expiry_str)
    if not option_chain:
        return None

    entry_dt = datetime.combine(sim_date, datetime.strptime(config.ENTRY_TIME, '%H:%M').time())
    exit_dt = datetime.combine(sim_date, datetime.strptime(config.EXIT_TIME, '%H:%M').time())

    # --- 1. Strike Selection ---
    spot_price = get_price_at_time(security_id, entry_dt, instrument_type='INDEX')
    if spot_price == 0.0:
        print(f"Could not fetch spot price at {entry_dt}. Skipping simulation.")
        return None
    print(f"Spot price at {config.ENTRY_TIME}: {spot_price}")

    # Round to nearest 100 for strike price
    short_ce_strike = round((spot_price + config.SHORT_OTM_DISTANCE) / 100) * 100
    short_pe_strike = round((spot_price - config.SHORT_OTM_DISTANCE) / 100) * 100
    hedge_ce_strike = short_ce_strike + config.HEDGE_DISTANCE
    hedge_pe_strike = short_pe_strike - config.HEDGE_DISTANCE

    print(f"Calculated Strikes -> Short CE: {short_ce_strike}, Hedge CE: {hedge_ce_strike}")
    print(f"Calculated Strikes -> Short PE: {short_pe_strike}, Hedge PE: {hedge_pe_strike}")

    # --- 2. Get Instrument IDs ---
    short_ce_id = find_option_instrument(option_chain, short_ce_strike, 'CE')
    hedge_ce_id = find_option_instrument(option_chain, hedge_ce_strike, 'CE')
    short_pe_id = find_option_instrument(option_chain, short_pe_strike, 'PE')
    hedge_pe_id = find_option_instrument(option_chain, hedge_pe_strike, 'PE')

    if not all([short_ce_id, hedge_ce_id, short_pe_id, hedge_pe_id]):
        print("Could not find all required option instruments. Skipping.")
        return None

    # --- 3. Simulated Entry ---
    trade_log = {'Date': sim_date.strftime('%Y-%m-%d'), 'Spot Price': spot_price}

    short_ce_premium = get_price_at_time(short_ce_id, entry_dt)
    hedge_ce_premium = get_price_at_time(hedge_ce_id, entry_dt)
    short_pe_premium = get_price_at_time(short_pe_id, entry_dt)
    hedge_pe_premium = get_price_at_time(hedge_pe_id, entry_dt)

    trade_log.update({
        'Short CE Strike': short_ce_strike, 'Short CE Premium': short_ce_premium,
        'Hedge CE Strike': hedge_ce_strike, 'Hedge CE Premium': hedge_ce_premium,
        'Short PE Strike': short_pe_strike, 'Short PE Premium': short_pe_premium,
        'Hedge PE Strike': hedge_pe_strike, 'Hedge PE Premium': hedge_pe_premium,
    })

    net_credit = (short_ce_premium + short_pe_premium) - (hedge_ce_premium + hedge_pe_premium)
    trade_log['Net Credit'] = net_credit
    print(f"Net Credit: {net_credit:.2f}")

    # --- 4. SL Calculation & Monitoring ---
    short_ce_sl = short_ce_premium * (1 + config.PREMIUM_SL_PERCENTAGE)
    short_pe_sl = short_pe_premium * (1 + config.PREMIUM_SL_PERCENTAGE)
    trade_log.update({'Short CE SL': short_ce_sl, 'Short PE SL': short_pe_sl})

    # Initialize exits
    short_ce_exit, short_pe_exit = None, None

    # Check CE SL
    ce_history = get_intraday_price_history(short_ce_id, sim_date)
    if not ce_history.empty:
        sl_hit_ce = ce_history[(ce_history['datetime'] > entry_dt) & (ce_history['high'] >= short_ce_sl)]
        if not sl_hit_ce.empty:
            short_ce_exit = short_ce_sl
            print(f"SL HIT for Short CE at {sl_hit_ce.iloc[0]['datetime']}")

    # Check PE SL
    pe_history = get_intraday_price_history(short_pe_id, sim_date)
    if not pe_history.empty:
        sl_hit_pe = pe_history[(pe_history['datetime'] > entry_dt) & (pe_history['high'] >= short_pe_sl)]
        if not sl_hit_pe.empty:
            short_pe_exit = short_pe_sl
            print(f"SL HIT for Short PE at {sl_hit_pe.iloc[0]['datetime']}")

    # --- 5. Final Exit ---
    trade_log['Short CE Exit Price'] = short_ce_exit if short_ce_exit else get_price_at_time(short_ce_id, exit_dt)
    trade_log['Hedge CE Exit Price'] = get_price_at_time(hedge_ce_id, exit_dt)
    trade_log['Short PE Exit Price'] = short_pe_exit if short_pe_exit else get_price_at_time(short_pe_id, exit_dt)
    trade_log['Hedge PE Exit Price'] = get_price_at_time(hedge_pe_id, exit_dt)

    # --- 6. P/L Calculation ---
    # Assuming lot size of 15 for Bank Nifty
    lot_size = 15
    pl_short_ce = (short_ce_premium - trade_log['Short CE Exit Price']) * lot_size
    pl_hedge_ce = (trade_log['Hedge CE Exit Price'] - hedge_ce_premium) * lot_size
    pl_short_pe = (short_pe_premium - trade_log['Short PE Exit Price']) * lot_size
    pl_hedge_pe = (trade_log['Hedge PE Exit Price'] - hedge_pe_premium) * lot_size

    total_pl = pl_short_ce + pl_hedge_ce + pl_short_pe + pl_hedge_pe

    trade_log.update({
        'Short CE P/L': pl_short_ce, 'Short PE P/L': pl_short_pe,
        'Total P/L': total_pl
    })

    print(f"Total P/L for the day: {total_pl:.2f}")
    return trade_log


def main():
    """Main function to run the simulation."""
    # For demonstration, we run it for the previous weekday.
    # You can loop through a list of dates to backtest over a period.
    today = date.today()
    sim_date = today - timedelta(days=1)

    # Find the last weekday
    while sim_date.weekday() > 4: # 0-4 are Mon-Fri
        sim_date -= timedelta(days=1)

    result = run_simulation(sim_date)

    if result:
        print("\n--- Simulation Result ---")
        result_series = pd.Series(result)
        print(result_series)
        export_to_excel(result)


import os

def export_to_excel(trade_log):
    """Exports the trade log dictionary to an Excel file."""
    if not trade_log:
        return

    df = pd.DataFrame([trade_log])
    filename = config.EXCEL_FILE_NAME

    # Define the desired column order
    columns = [
        'Date', 'Spot Price',
        'Short CE Strike', 'Short CE Premium', 'Short CE SL', 'Short CE Exit Price', 'Short CE P/L',
        'Hedge CE Strike', 'Hedge CE Premium', 'Hedge CE Exit Price',
        'Short PE Strike', 'Short PE Premium', 'Short PE SL', 'Short PE Exit Price', 'Short PE P/L',
        'Hedge PE Strike', 'Hedge PE Premium', 'Hedge PE Exit Price',
        'Net Credit', 'Total P/L'
    ]
    df = df[columns]

    try:
        # Check if file exists to determine if we need to write headers
        file_exists = os.path.isfile(filename)

        with pd.ExcelWriter(filename, mode='a' if file_exists else 'w', engine='openpyxl', if_sheet_exists='overlay' if file_exists else None) as writer:
            if file_exists:
                # Find the last row in the 'Trades' sheet and append after it
                startrow = writer.book['Trades'].max_row
                df.to_excel(writer, index=False, header=False, sheet_name='Trades', startrow=startrow)
            else:
                # If the file is new, write with header
                df.to_excel(writer, index=False, header=True, sheet_name='Trades')

        print(f"Successfully exported trade to {filename}")

    except Exception as e:
        print(f"Error exporting to Excel: {e}")


if __name__ == "__main__":
    main()
