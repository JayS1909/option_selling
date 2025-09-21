# -- Dhan API Credentials --
# Replace with your actual Client ID and Access Token
DHAN_CLIENT_ID = "YOUR_CLIENT_ID"
DHAN_ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"

# -- Strategy Parameters --
# Symbol to trade
TRADING_SYMBOL = "BANKNIFTY"
# OTM distance for short legs (in points)
SHORT_OTM_DISTANCE = 300
# Distance from short strikes to hedge strikes (in points)
HEDGE_DISTANCE = 500 # e.g., 400-500 points away from short strike

# -- Stop Loss Parameters --
# Stop loss for short legs as a percentage of the premium received (e.g., 0.2 for 20%)
PREMIUM_SL_PERCENTAGE = 0.25 # 25%

# -- Timing --
ENTRY_TIME = "09:20"
EXIT_TIME = "15:00"

# -- Expiry & Spot Price --
# IMPORTANT: You must manually set these values before running the simulation.

# Set the weekly expiry date. Format: 'DD-MM-YYYY' (e.g., '26-10-2023')
MANUAL_EXPIRY_DATE = "19-09-2025" #<-- PLEASE CHANGE THIS

# Set the spot price of the index at 9:20 AM for the simulation day.
MANUAL_SPOT_PRICE = 48000.0 #<-- PLEASE CHANGE THIS

# -- Output --
EXCEL_FILE_NAME = "simulation_log.xlsx"
