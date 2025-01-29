import csv
from collections import deque
import logging
import os

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,  # Feel free to change to INFO to reduce verbosity
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]  # console only
)

class Inventory:
    def __init__(self):
        # LIFO: pop from the right
        self.inventory = deque()
        self.current_inventory = 0

    def add_inventory(self, quantity, price):
        """
        Add 'quantity' units to the inventory at 'price' cost each.
        """
        self.inventory.append({"quantity": quantity, "price": price})
        self.current_inventory += quantity
        logger.debug(f"[add_inventory] Added => QTY: {quantity}, Price: {price}, New current: {self.current_inventory}")

    def sell_inventory(self, quantity_to_sell, sell_price):
        """
        Sell 'quantity_to_sell' units from the inventory using LIFO.
        'sell_price' is the price at which we sold it (revenue side).
        Returns: (cogs, loss)
        """
        cogs = 0
        remaining_quantity = quantity_to_sell
        loss = 0  # Track loss if selling below cost

        logger.debug(f"[sell_inventory] Starting LIFO sale => Sell: {quantity_to_sell}, Price: {sell_price}")

        while remaining_quantity > 0 and self.inventory:
            recent_batch = self.inventory.pop()  # LIFO
            batch_quantity = recent_batch["quantity"]
            batch_price = recent_batch["price"]

            if batch_quantity <= remaining_quantity:
                # Sell the entire batch
                cogs += batch_quantity * batch_price
                remaining_quantity -= batch_quantity
                self.current_inventory -= batch_quantity
                logger.debug(
                    f"[sell_inventory] Selling entire batch => "
                    f"BatchQty: {batch_quantity}, BatchPrice: {batch_price}, "
                    f"RemainingQtyToSell: {remaining_quantity}, Updated current_inventory: {self.current_inventory}"
                )
            else:
                # Only sell part of the batch
                cogs += remaining_quantity * batch_price
                recent_batch["quantity"] -= remaining_quantity
                self.inventory.append(recent_batch)
                self.current_inventory -= remaining_quantity
                logger.debug(
                    f"[sell_inventory] Selling partial batch => SellQty: {remaining_quantity}, "
                    f"RemainingBatchQty: {recent_batch['quantity']}, Updated current_inventory: {self.current_inventory}"
                )
                remaining_quantity = 0

        # Calculate potential loss (if total revenue < COGS)
        total_revenue_from_sale = quantity_to_sell * sell_price
        if total_revenue_from_sale < cogs:
            loss = cogs - total_revenue_from_sale
            logger.debug(
                f"[sell_inventory] Sale resulted in a loss => "
                f"COGS: {cogs}, Revenue: {total_revenue_from_sale}, Loss: {loss}"
            )

        return cogs, loss

def main():
    """
    Main function to read a CSV file (data_total_final2.csv),
    process inventory in LIFO order, and produce a daily report (daily_report.csv).
    """
    logger.info("[main] Starting LIFO read script...")

    inventory = Inventory()
    daily_report = []

    csv_file = "data_total_final2.csv"
    output_file = "daily_report.csv"

    # Check if data_total_final2.csv actually exists and has content
    if not os.path.exists(csv_file):
        logger.error(f"[main] {csv_file} not found. Exiting.")
        return
    else:
        file_size = os.path.getsize(csv_file)
        logger.debug(f"[main] {csv_file} found. Size: {file_size} bytes")

    with open(csv_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        rows_read = 0

        for row in reader:
            rows_read += 1
            logger.debug(f"[main] Row {rows_read} => {row}")

            date = row["timestamp"].split("T")[0] if row["timestamp"] else "N/A"
            received = float(row["received"]) if row["received"] else 0.0
            sold = float(row["sold"]) if row["sold"] else 0.0
            price = float(row["price"]) if row["price"] else 0.0

            beginning_inventory = inventory.current_inventory
            daily_revenue = 0
            daily_cogs = 0
            daily_profit_loss = 0
            gross_margin_percentage = 0
            loss = 0

            # If we received some quantity, treat it as an "inventory purchase" at that price
            #
            # NOTE: This is conceptually reversed if you consider "received" as a new supply
            #       rather than revenue from a sale. But we leave the logic as-is.
            if received > 0:
                logger.debug(f"[main] Date {date}: Received={received} at Price={price}")
                revenue = received * price
                daily_revenue += revenue
                inventory.add_inventory(received, price)

            # If we sold some quantity, compute COGS via LIFO
            if sold > 0:
                cogs, loss = inventory.sell_inventory(sold, price)
                daily_cogs += cogs

                # daily_revenue so far includes "revenue" from 'received'
                # per the original code. This is unorthodox but kept unchanged.
                daily_profit_loss = daily_revenue - daily_cogs - loss

                if daily_revenue > 0:
                    gross_margin_percentage = (daily_profit_loss / daily_revenue) * 100

            ending_inventory = inventory.current_inventory
            net_inventory_movement = received - sold

            daily_report.append({
                "timestamp": date,
                "beginning_inventory": round(beginning_inventory, 6),
                "received": round(received, 6),
                "sold_quantity": round(sold, 6),
                "daily_revenue": round(daily_revenue, 2),
                "daily_cogs": round(daily_cogs, 2),
                "gross_profit": round(daily_profit_loss, 2),
                "total_loss": round(loss, 2),
                "net_inventory_movement": round(net_inventory_movement, 6),
                "ending_inventory": round(ending_inventory, 6),
                "gross_margin_percentage": round(gross_margin_percentage, 2)
            })

        logger.info(f"[main] Finished reading CSV: {rows_read} rows processed.")

    # Write daily report
    try:
        with open(output_file, mode="w", newline="") as csvfile:
            fieldnames = [
                "timestamp", "beginning_inventory", "received", "sold_quantity",
                "daily_revenue", "daily_cogs", "gross_profit", "total_loss",
                "net_inventory_movement", "ending_inventory", "gross_margin_percentage"
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(daily_report)

        logger.info(f"[main] Daily report successfully written to {output_file}")
    except Exception as e:
        logger.error(f"[main] Error writing daily report: {e}")

if __name__ == "__main__":
    main()
