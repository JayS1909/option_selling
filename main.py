import config
from dhanhq import dhanhq

print("--- Starting Debug Script ---")

try:
    # Initialize the client
    dhan = dhanhq(config.DHAN_CLIENT_ID, config.DHAN_ACCESS_TOKEN)
    print("Dhan API client initialized successfully.")

    # Print all available methods and attributes
    print("\n--- Available DhanHQ Methods ---")
    print("Below is a list of all functions available. Please copy this entire list and send it back.")
    print(dir(dhan))
    print("--------------------------------\n")

except Exception as e:
    print(f"Error during initialization: {e}")

print("--- Debug Script Finished ---")
