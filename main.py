import config
import pandas as pd
from datetime import datetime, date, timedelta
from dhanhq import dhanhq
import os

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
    if symbol == "BANKNIFTY":
        return 26009

    print(f"Attempting to find security ID for {symbol} from security list (this may be slow)...")
    try:
        df = dhan.fetch_security_list()

        fno_security = df[(df['SEM_INSTRUMENT_NAME'] == symbol) & (df['SEM_EXM_EXCH_ID'] == 'NSE_FNO')]
        if not fno_security.empty:
            return fno_security.iloc[0]['SEM_SMST_SECURITY_ID']

    except Exception as e:
        print(f"Could not fetch from security list or find symbol. Error: {e}")

    print(f"Security ID for {symbol} not found.")
    return None


def get_nearest_weekly_expiry(symbol_name='BANKNIFTY'):
    """
    Finds the nearest weekly expiry date by fetching the scrip master list.
    This is a more reliable method.
    """
    print("Fetching security list to find expiry dates...")
    try:
        df = dhan.fetch_security_list()

        df_options = df[
            (df['SEM_INSTRUMENT_NAME'] == symbol_name) &
            (df['SEM_EXCH_INSTRUMENT_TYPE'] == 'OPTIDX') &
            (df['SEM_EXM_EXCH_ID'] == 'NSE_FNO')
        ]

        expiries = pd.to_datetime(df_options['SEM_EXPIRY_DATE'], format='%Y%m%d').dt.date.unique()

        today = date.today()
        future_expiries = sorted([exp for exp in expiries if exp >= today])

        if future_expiries:
            print(f"Found nearest expiry: {future_expiries[0]}")
            return future_expiries[0].strftime('%d-%m-%Y')

    except Exception as e:
        print(f"Error fetching or processing scrip master for expiry dates: {e}")

    return None

def get_option_chain(security_id, expiry_date):
    """Fetches the option chain for a given security ID and expiry."""
    try:
        option_chain_data = dhan.option_chain(str(security_id), expiry_date)
        return option_chain_data['data']['option_chains']
    except Exception as e:
        print(f"Error fetching option chain: {e}")
        return None

def get_price_at_time(instrument_id, target_dt, exchange='NSE_FNO', instrument_type='OPTIDX'):
    """Gets the closing price of an instrument at a specific time."""
    from_date = to_date = target_dt.strftime('%Y-%m-%d')

    if instrument_type == 'INDEX':
        instrument_type = 'INDICES'
        exchange = 'NSE_INDEX'

    try:
        hist_data = dhan.intraday_minute_data(
            security_id=str(instrument_id),
            exchange_segment=exchange,
            instrument_type=instrument_type,
            from_date=from_date,
            to_date=to_date
        )

        if hist_data.get('status') == 'success':
            df = pd.DataFrame(hist_data)
            df['datetime'] = pd.to_datetime(df['start_Time'], unit='s')

            target_candle = df[df['datetime'] == target_dt]
            if not target_candle.empty:
                return target_candle.iloc[0]['close']
            else:
                print(f"No data found at exact time {target_dt} for {instrument_id}. Using nearest available.")
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
        hist_data = dhan.intraday_minute_data(
            security_id=str(instrument_id),
            exchange_segment=exchange,
            instrument_type=instrument_type,
            from_date=from_date,
            to_date=to_date
        )
        if hist_data.get('status') == 'success':
            df = pd.DataFrame(hist_data)
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

    security_id = get_security_id(config.TRADING_SYMBOL)
    if not security_id:
        return None

    expiry_str = get_nearest_weekly_expiry(config.TRADING_SYMBOL)
    if not expiry_str:
        print("Could not find expiry date.")
        return None

    option_chain = get_option_chain(security_id, expiry_str)
    if not option_chain:
        return None

    entry_dt = datetime.combine(sim_date, datetime.strptime(config.ENTRY_TIME, '%H:%M').time())
    exit_dt = datetime.combine(sim_date, datetime.strptime(config.EXIT_TIME, '%H:%M').time())

    spot_price = get_price_at_time(security_id, entry_dt, instrument_type='INDEX')
    if spot_price == 0.0:
        print(f"Could not fetch spot price at {entry_dt}. Skipping simulation.")
        return None
    print(f"Spot price at {config.ENTRY_TIME}: {spot_price}")

    short_ce_strike = round((spot_price + config.SHORT_OTM_DISTANCE) / 100) * 100
    short_pe_strike = round((spot_price - config.SHORT_OTM_DISTANCE) / 100) * 100
    hedge_ce_strike = short_ce_strike + config.HEDGE_DISTANCE
    hedge_pe_strike = short_pe_strike - config.HEDGE_DISTANCE

    print(f"Calculated Strikes -> Short CE: {short_ce_strike}, Hedge CE: {hedge_ce_strike}")
    print(f"Calculated Strikes -> Short PE: {short_pe_strike}, Hedge PE: {hedge_pe_strike}")

    short_ce_id = find_option_instrument(option_chain, short_ce_strike, 'CE')
    hedge_ce_id = find_option_instrument(option_chain, hedge_ce_strike, 'CE')
    short_pe_id = find_option_instrument(option_chain, short_pe_strike, 'PE')
    hedge_pe_id = find_option_instrument(option_chain, hedge_pe_strike, 'PE')

    if not all([short_ce_id, hedge_ce_id, short_pe_id, hedge_pe_id]):
        print("Could not find all required option instruments. Skipping.")
        return None

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

    short_ce_sl = short_ce_premium * (1 + config.PREMIUM_SL_PERCENTAGE)
    short_pe_sl = short_pe_premium * (1 + config.PREMIUM_SL_PERCENTAGE)
    trade_log.update({'Short CE SL': short_ce_sl, 'Short PE SL': short_pe_sl})

    short_ce_exit, short_pe_exit = None, None

    ce_history = get_intraday_price_history(short_ce_id, sim_date)
    if not ce_history.empty:
        sl_hit_ce = ce_history[(ce_history['datetime'] > entry_dt) & (ce_history['high'] >= short_ce_sl)]
        if not sl_hit_ce.empty:
            short_ce_exit = short_ce_sl
            print(f"SL HIT for Short CE at {sl_hit_ce.iloc[0]['datetime']}")

    pe_history = get_intraday_price_history(short_pe_id, sim_date)
    if not pe_history.empty:
        sl_hit_pe = pe_history[(pe_history['datetime'] > entry_dt) & (pe_history['high'] >= short_pe_sl)]
        if not sl_hit_pe.empty:
            short_pe_exit = short_pe_sl
            print(f"SL HIT for Short PE at {sl_hit_pe.iloc[0]['datetime']}")

    trade_log['Short CE Exit Price'] = short_ce_exit if short_ce_exit else get_price_at_time(short_ce_id, exit_dt)
    trade_log['Hedge CE Exit Price'] = get_price_at_time(hedge_ce_id, exit_dt)
    trade_log['Short PE Exit Price'] = short_pe_exit if short_pe_exit else get_price_at_time(short_pe_id, exit_dt)
    trade_log['Hedge PE Exit Price'] = get_price_at_time(hedge_pe_id, exit_dt)

    lot_size = 15
    pl_short_ce = (short_ce_premium - trade_log['Short CE Exit Price']) * lot_size
    pl_hedge_ce = (trade_log['Hedge CE Exit Price'] - hedge_ce_premium) * lot_size
    pl_short_pe = (short_pe_premium - trade_log['Short PE Exit Price']) * lot_size
    pl_hedge_pe = (trade_log['Hedge PE Exit Price'] - hedge_pe_premium) * lot_size

    total_pl = pl_short_ce + pl_hedge_ce + pl_short_pe + pl_hedge_pe

    trade_log.update({
        'Short CE P/L': pl_short_ce, 'Hedge CE P/L': pl_hedge_ce,
        'Short PE P/L': pl_short_pe, 'Hedge PE P/L': pl_hedge_pe,
        'Total P/L': total_pl
    })

    print(f"Total P/L for the day: {total_pl:.2f}")
    return trade_log


def main():
    """Main function to run the simulation."""
    today = date.today()
    sim_date = today - timedelta(days=1)

    while sim_date.weekday() > 4:
        sim_date -= timedelta(days=1)

    result = run_simulation(sim_date)

    if result:
        print("\n--- Simulation Result ---")
        result_series = pd.Series(result)
        print(result_series)
        export_to_excel(result)


def export_to_excel(trade_log):
    """
    Exports the trade log dictionary to an Excel file.
    This function correctly handles appending new rows to an existing file.
    """
    if not trade_log:
        return

    new_df = pd.DataFrame([trade_log])
    filename = config.EXCEL_FILE_NAME

    columns = [
        'Date', 'Spot Price',
        'Short CE Strike', 'Short CE Premium', 'Short CE SL', 'Short CE Exit Price', 'Short CE P/L',
        'Hedge CE Strike', 'Hedge CE Premium', 'Hedge CE Exit Price', 'Hedge CE P/L',
        'Short PE Strike', 'Short PE Premium', 'Short PE SL', 'Short PE Exit Price', 'Short PE P/L',
        'Hedge PE Strike', 'Hedge PE Premium', 'Hedge PE Exit Price', 'Hedge PE P/L',
        'Net Credit', 'Total P/L'
    ]
    new_df = new_df[columns]

    try:
        if os.path.isfile(filename):
            existing_df = pd.read_excel(filename)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df

        combined_df.to_excel(filename, index=False, sheet_name='Trades')

        print(f"Successfully exported trade to {filename}")

    except Exception as e:
        print(f"Error exporting to Excel: {e}")


if __name__ == "__main__":
    main()
