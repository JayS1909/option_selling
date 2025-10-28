# -- Dhan API Credentials --
# Please enter your Dhan Client ID and Access Token below.
# The Access Token can be generated from web.dhan.co
DHAN_CLIENT_ID = "YOUR_CLIENT_ID"
DHAN_ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"

# -- Strategy Parameters --
TRADING_SYMBOL = "BANKNIFTY"
# OTM distance for short legs in steps (1 step = 100 points for BANKNIFTY)
# 300 points = 3 steps
SHORT_OTM_STEPS = 3
# Hedge distance from short strikes in steps
# 400 points away from short strike = 4 steps from ATM + 3 steps OTM = 7 steps total from ATM
HEDGE_OTM_STEPS = 7 # 3 for short + 4 for hedge distance

# -- Output --
EXCEL_FILE_NAME = "live_trade_log.xlsx"
