import json
import time
import traceback
from datetime import datetime, timedelta, UTC
import csv
import requests
import logging

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,  # You can switch to INFO if logs are too verbose
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]  # console only; you could add a FileHandler
)

API_KEY = "TAOSTATS_API"

_SECONDARY_WALLETS = [
    # Example: "5FEXAMPLE..."
]

_WALLETS = [
    "5xxxx",
]

_SELL_WALLETS = [
    # Include wallets that you consider "sell" destinations
]


def remove_value_from_list(value, lst):
    if value in lst:
        lst.remove(value)
    return lst


def get_historical_tao_prices():
    """Fetch TAO price data from MEXC (TAOUSDT)."""
    logger.debug("Fetching historical TAO prices from MEXC...")
    symbol = "TAOUSDT"
    interval = "1d"
    start_time = datetime(2023, 11, 1)  # Example start date
    end_time = datetime.now()

    url = "https://api.mexc.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": 1000}

    if start_time:
        params["startTime"] = int(start_time.timestamp() * 1000)
    if end_time:
        params["endTime"] = int(end_time.timestamp() * 1000)

    response = requests.get(url, params=params)
    data = response.json()

    historical_data = []
    for entry in data:
        historical_data.append({
            "timestamp": datetime.fromtimestamp(entry[0] / 1000, UTC),
            "open": float(entry[1]),
            "high": float(entry[2]),
            "low": float(entry[3]),
            "close": float(entry[4]),
            "volume": float(entry[5]),
        })

    logger.debug(f"Fetched {len(historical_data)} days of price data.")
    return historical_data


def subtract_one_day(day):
    """Subtract one day from a string datetime in ISO format."""
    try:
        dt = datetime.strptime(day, "%Y-%m-%dT%H:%M:%S.%f")
    except ValueError:
        dt = datetime.strptime(day, "%Y-%m-%dT%H:%M:%S")
    new_dt = dt - timedelta(days=1)
    new_timestamp = new_dt.strftime("%Y-%m-%dT00:00:00.00")
    return new_timestamp


def add_one_day(day):
    """Add one day to a string datetime in ISO format."""
    try:
        dt = datetime.strptime(day, "%Y-%m-%dT%H:%M:%S.%f")
    except ValueError:
        dt = datetime.strptime(day, "%Y-%m-%dT%H:%M:%S")
    new_dt = dt + timedelta(days=1)
    new_timestamp = new_dt.strftime("%Y-%m-%dT00:00:00.00")
    return new_timestamp


def convert_to_tao(rao):
    """Convert raw Rao to TAO (divide by 1e9)."""
    return int(rao) / 1_000_000_000


def format_date(ts):
    """Format the timestamp to 'YYYY-MM-DDT00:00:00.00'."""
    try:
        dt = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S.%fZ')
    except Exception:
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
    return dt.strftime("%Y-%m-%dT00:00:00.00")


def get_wallet_historical_balances(wallet):
    """
    Retrieve historical balances for a specific wallet (taostats.io).
    Uses pagination, waiting 30s between pages to avoid rate limits.
    """
    logger.info(f"Fetching historical balances for wallet: {wallet}")
    headers = {"accept": "application/json", "Authorization": API_KEY}

    all_nodes = []
    page = 1
    max_pages = 0

    while True:
        logger.debug(f"Sleep 30s before next API request for balances (page {page})...")
        time.sleep(30)
        url = f"https://api.taostats.io/api/account/history/v1?address={wallet}&page={page}&limit=200"
        response = requests.get(url, headers=headers)

        try:
            data_json = response.json()
        except Exception as e:
            logger.error(f"Error parsing JSON (balances): {e}")
            break

        if "data" not in data_json or "pagination" not in data_json:
            logger.warning(f"Unexpected structure (balances). Raw response: {data_json}")
            break

        # Set max_pages only once (unless it's 0, in which case we break immediately)
        if max_pages == 0:
            max_pages = data_json["pagination"]["total_pages"]
            logger.debug(f"Max pages for balance history: {max_pages}")

            # FIX: If total_pages=0, break to avoid infinite loop
            if max_pages == 0:
                logger.debug(f"No historical balance pages for wallet {wallet}. Breaking loop.")
                break

        all_nodes.append(data_json["data"])

        if page == max_pages:
            break
        page += 1

    logger.debug(f"Fetched historical balances for wallet {wallet}. Pages: {max_pages}")
    return all_nodes


def get_wallet_transfers(wallet, outbound=True):
    """
    Retrieve transfer records (inbound/outbound) for a given wallet (taostats.io).
    Uses pagination, waiting 30s between pages to avoid rate limits.
    """
    headers = {"accept": "application/json", "Authorization": API_KEY}
    direction = "outbound" if outbound else "inbound"
    logger.info(f"Fetching {direction} transfers for wallet: {wallet}")

    all_nodes = []
    page = 1
    max_pages = 0

    while True:
        logger.debug(f"Sleep 30s before next API request for transfers (page {page})...")
        time.sleep(30)

        if outbound:
            url = f"https://api.taostats.io/api/transfer/v1?address={wallet}&from={wallet}&page={page}&limit=200"
        else:
            url = f"https://api.taostats.io/api/transfer/v1?address={wallet}&to={wallet}&page={page}&limit=200"

        response = requests.get(url, headers=headers)

        try:
            data_json = response.json()
        except Exception as e:
            logger.error(f"Error parsing JSON for transfers: {e}")
            break

        if "data" not in data_json or "pagination" not in data_json:
            logger.warning(f"Unexpected structure for transfers. Response: {data_json}")
            break

        if max_pages == 0:
            max_pages = data_json["pagination"]["total_pages"]
            logger.debug(f"Max pages for {direction} transfers: {max_pages}")

            # FIX: If total_pages=0, break to avoid infinite loop (page never equals 0)
            if max_pages == 0:
                logger.debug(f"No {direction} transfers at all for wallet {wallet}. Breaking loop.")
                break

        all_nodes.append(data_json["data"])

        if page == max_pages:
            break
        page += 1

    logger.debug(f"Fetched {direction} transfers for wallet {wallet}. Pages: {max_pages}")
    return all_nodes


def get_block_height_timestamp(block):
    """
    Retrieve timestamp for a given block using taostats.io.
    """
    headers = {"accept": "application/json", "Authorization": API_KEY}
    url = f"https://api.taostats.io/api/block/v1?block_number={block}"

    logger.debug(f"Fetching timestamp for block {block}...")
    response = requests.get(url, headers=headers)

    try:
        data_json = response.json()
        if "data" in data_json and len(data_json["data"]) > 0:
            return data_json["data"][0]["timestamp"]
    except Exception as e:
        logger.error(f"Error parsing JSON when fetching block timestamp: {e}")

    return None


# ---------------------------
# Main logic to gather data
# ---------------------------

def main():
    logger.info("Starting data-gathering process...")
    all_final_data = {}

    # This will store combined daily data from all wallets
    all_final_data_total = {}
    all_final_data_combined = {}

    if not _WALLETS:
        logger.warning("No wallets in _WALLETS. You must populate _WALLETS for data to be collected.")
    else:
        # Get data for each wallet
        for w_idx, _WALLET in enumerate(_WALLETS, start=1):
            logger.info(f"Processing wallet #{w_idx}/{len(_WALLETS)}: {_WALLET}")

            final_data = {}
            file_path = f"historical_data_{_WALLET}.json"

            try:
                with open(file_path, "r") as file:
                    final_data = json.load(file)
                    logger.debug(f"Loaded existing JSON for {_WALLET}.")
            except Exception:
                logger.debug(f"JSON file {file_path} doesn't exist; fetching new data for {_WALLET}.")
                account_balances = get_wallet_historical_balances(_WALLET)
                wallet_outbound_extrinsics = get_wallet_transfers(_WALLET, outbound=True)
                wallet_inbound_extrinsics = get_wallet_transfers(_WALLET, outbound=False)

                # Merge into final_data
                for account_balance_page in account_balances:
                    for row in account_balance_page:
                        formatted_date = format_date(row["timestamp"])
                        row["day"] = formatted_date
                        final_data[formatted_date] = row

                for transfers_page in wallet_outbound_extrinsics:
                    for row in transfers_page:
                        day = format_date(row["timestamp"])
                        if day not in final_data:
                            final_data[day] = {}
                        if "transfers" not in final_data[day]:
                            final_data[day]["transfers"] = []
                        final_data[day]["transfers"].append(row)

                for inbound_page in wallet_inbound_extrinsics:
                    for row in inbound_page:
                        day = format_date(row["timestamp"])
                        if day not in final_data:
                            final_data[day] = {}
                        if "inbound_transfers" not in final_data[day]:
                            final_data[day]["inbound_transfers"] = []
                        final_data[day]["inbound_transfers"].append(row)

                # Write the final_data to a JSON file for caching
                with open(file_path, "w") as file:
                    json.dump(final_data, file, indent=4)
                logger.info(f"Wrote new JSON data to {file_path}")

            all_final_data[_WALLET] = final_data

        # Process final_data for each wallet to build daily totals
        for ck, final_data in all_final_data.items():
            # Sort by date string
            sorted_final_data = dict(sorted(
                final_data.items(),
                key=lambda item: datetime.strptime(item[0], "%Y-%m-%dT%H:%M:%S.%f")
            ))
            final_day_total = {}
            leftover_transfers_day = {}
            leftover_sold_day = {}
            leftover_inbound_transfer_day = {}

            for d, r in sorted_final_data.items():
                # Summaries
                totaled_transfer = 0
                sold_transfer = 0
                inbound_transfers = 0

                subtracted_day = subtract_one_day(d)

                # Outbound transfers
                if "transfers" in r:
                    # Potentially we compare times with r["timestamp"] if needed
                    totaled_transfer = sum(int(i["amount"]) for i in r["transfers"])
                    sold_transfer = sum(
                        int(i["amount"]) for i in r["transfers"]
                        if i.get("to", {}).get("ss58") in _SELL_WALLETS
                    )

                # Inbound transfers
                if "inbound_transfers" in r:
                    inbound_transfers = sum(int(i["amount"]) for i in r["inbound_transfers"])

                logger.debug(
                    f"Wallet {ck} - Day {d}: Outbound={totaled_transfer}, "
                    f"Sold={sold_transfer}, Inbound={inbound_transfers}"
                )

                # Combine leftover logic from previous day
                if subtracted_day in leftover_transfers_day:
                    totaled_transfer += leftover_transfers_day[subtracted_day]
                    sold_transfer += leftover_sold_day[subtracted_day]
                if subtracted_day in leftover_inbound_transfer_day:
                    inbound_transfers += leftover_inbound_transfer_day[subtracted_day]

                # Attempt to get day_total from the JSON structure
                try:
                    balance_total = int(r["balance_total"])
                except KeyError:
                    balance_total = 0

                # day_total is the wallet's total balance on that day
                day_total = balance_total

                # Compare to previous day
                try:
                    previous_received = final_day_total[subtracted_day]["day_total"]
                except KeyError:
                    previous_received = 0

                today_diff = convert_to_tao(day_total) - previous_received

                final_day_total[d] = {
                    "day_total": convert_to_tao(day_total),
                    "total_transferred": convert_to_tao(totaled_transfer) - convert_to_tao(inbound_transfers),
                    "received": today_diff
                                + convert_to_tao(totaled_transfer)
                                - convert_to_tao(inbound_transfers),
                    "sold_transferred": convert_to_tao(sold_transfer),
                }

            # Merge into all_final_data_total (by wallet)
            all_final_data_total[ck] = final_day_total

        # Combine across all wallets
        for ck, v in all_final_data_total.items():
            for d, total in v.items():
                # If total["received"] < 0, we might clamp it or leave it as-is
                if total["received"] < 0:
                    # The original snippet might have set it to 0 or tried to fix it
                    # We'll leave as-is or set to 0 if you prefer:
                    pass

                # If this wallet is a secondary wallet, skip large "received" values
                if ck in _SECONDARY_WALLETS:
                    if total["received"] > 2:
                        total["received"] = 0.0

                if d not in all_final_data_combined:
                    all_final_data_combined[d] = {
                        "received": total["received"],
                        "sold_transferred": total["sold_transferred"]
                    }
                else:
                    all_final_data_combined[d]["received"] += total["received"]
                    all_final_data_combined[d]["sold_transferred"] += total["sold_transferred"]

    # Grab historical TAO prices
    logger.info("Fetching historical TAO prices to merge with daily data...")
    historical_prices = get_historical_tao_prices()
    price_map = {}
    for hp in historical_prices:
        # Key by date in the same format: 'YYYY-MM-DDT00:00:00.00'
        key_str = hp["timestamp"].strftime("%Y-%m-%dT00:00:00.00")
        price_map[key_str] = hp["close"]

    # Merge prices into the combined data
    for date_str in all_final_data_combined.keys():
        if date_str in price_map:
            all_final_data_combined[date_str]["tao_price"] = price_map[date_str]
        else:
            all_final_data_combined[date_str]["tao_price"] = 0.0  # or None if you prefer

    # Write CSV
    csv_file_path = "data_total_final2.csv"
    logger.info(f"Writing combined data to {csv_file_path}...")
    try:
        with open(csv_file_path, "w", newline="") as csv_file:
            writer = csv.writer(csv_file)
            header = ["timestamp", "received", "sold", "price", "total_received ($)", "total sold ($)"]
            writer.writerow(header)

            # Sort dates
            sorted_dates = sorted(
                all_final_data_combined.keys(),
                key=lambda d: datetime.strptime(d, "%Y-%m-%dT%H:%M:%S.%f")
            )

            for timestamp in sorted_dates:
                metrics = all_final_data_combined[timestamp]
                received_val = metrics.get("received", 0)
                sold_val = metrics.get("sold_transferred", 0)
                price_val = metrics.get("tao_price", 0)

                # Example clamp for large or negative 'received'
                if received_val > 250 or received_val < 0:
                    received_val = 0

                total_received_usd = received_val * price_val
                total_sold_usd = sold_val * price_val

                row = [timestamp, received_val, sold_val, price_val, total_received_usd, total_sold_usd]
                writer.writerow(row)

        logger.info(f"Done! Data written to {csv_file_path}")
    except Exception as e:
        logger.error(f"Error writing to {csv_file_path}: {e}")

if __name__ == "__main__":
    main()
