import os
import csv
import random
from datetime import datetime, timedelta

# Create directories if they don't exist
os.makedirs("c:/Users/jatin/ragprojects/project_1/backend/data", exist_ok=True)
os.makedirs("c:/Users/jatin/ragprojects/project_1/backend/models", exist_ok=True)

# Define merchant categories and typical merchants/amounts
DATA_TEMPLATE = {
    "Groceries": {
        "merchants": ["Walmart Supercenter", "Kroger Grocery", "Whole Foods Market", "Trader Joe's", "Safeway Store"],
        "min_amount": 15.0,
        "max_amount": 180.0
    },
    "Food & Dining": {
        "merchants": ["Starbucks Coffee", "McDonald's", "UberEats Delivery", "Dominos Pizza", "Chipotle Mexican Grill", "Subway Sandwiches", "Local Diner"],
        "min_amount": 5.0,
        "max_amount": 45.0
    },
    "Transport": {
        "merchants": ["Uber Trip", "Lyft Ride", "Chevron Gas", "Shell Fuel Station", "City Transit Subway", "ExxonMobil"],
        "min_amount": 8.0,
        "max_amount": 60.0
    },
    "Entertainment": {
        "merchants": ["Netflix.com", "Spotify Premium", "Hulu Subscription", "Steam Games", "AMC Theatres", "PlayStation Network"],
        "min_amount": 7.99,
        "max_amount": 29.99
    },
    "Utilities": {
        "merchants": ["Comcast Cable", "PG&E Electric", "Verizon Wireless", "AT&T Mobility", "City Water & Sewer"],
        "min_amount": 45.0,
        "max_amount": 180.0
    },
    "Shopping": {
        "merchants": ["Amazon.com", "Target Stores", "Best Buy", "Apple Store", "Nike Online", "Zara Fashion"],
        "min_amount": 10.0,
        "max_amount": 250.0
    }
}

def generate_transactions(num_rows, start_date_days_ago=90):
    transactions = []
    base_date = datetime.now() - timedelta(days=start_date_days_ago)
    
    for i in range(num_rows):
        # Pick category
        category = random.choice(list(DATA_TEMPLATE.keys()))
        template = DATA_TEMPLATE[category]
        
        # Pick random merchant and amount
        merchant = random.choice(template["merchants"])
        amount = round(random.uniform(template["min_amount"], template["max_amount"]), 2)
        
        # Pick random date within the window
        days_offset = random.randint(0, start_date_days_ago)
        hours_offset = random.randint(0, 23)
        minutes_offset = random.randint(0, 59)
        date = base_date + timedelta(days=days_offset, hours=hours_offset, minutes=minutes_offset)
        
        transactions.append({
            "date": date.strftime("%Y-%m-%d %H:%M:%S"),
            "description": merchant,
            "amount": amount,
            "category": category
        })
        
    # Sort transactions chronologically
    transactions.sort(key=lambda x: x["date"])
    return transactions

def save_csv(filepath, data, headers):
    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in data:
            writer.writerow(row)
    print(f"Successfully generated and saved {len(data)} rows to {filepath}")

def main():
    # 1. Generate Training Set (1000 rows of completely normal spending behavior)
    print("Generating training dataset...")
    train_data = generate_transactions(1000, start_date_days_ago=120)
    save_csv(
        "c:/Users/jatin/ragprojects/project_1/backend/data/transactions_train.csv",
        train_data,
        ["date", "description", "amount", "category"]
    )
    
    # 2. Generate Test Set (50 rows of normal transactions + injected anomalies)
    print("Generating testing dataset with anomalies...")
    test_data = generate_transactions(45, start_date_days_ago=30)
    
    # Inject deliberate anomalies that our Isolation Forest or rule engine should flag:
    anomalies = [
        # Anomaly A: Unusually large transaction amount (Outlier)
        {
            "date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"),
            "description": "Starbucks Coffee", 
            "amount": 450.00,  # Normally $5-$45
            "category": "Food & Dining"
        },
        # Anomaly B: Unrecognized sudden recurring software charge (Potential card fraud / forgotten sub)
        {
            "date": (datetime.now() - timedelta(days=12)).strftime("%Y-%m-%d %H:%M:%S"),
            "description": "Adobe Creative Cloud",  # Not in training set
            "amount": 54.99,
            "category": "Entertainment"
        },
        # Anomaly C: Massive Shopping outlier
        {
            "date": (datetime.now() - timedelta(days=18)).strftime("%Y-%m-%d %H:%M:%S"),
            "description": "Amazon.com", 
            "amount": 2899.99,  # Normally max $250
            "category": "Shopping"
        },
        # Anomaly D: Double charge / duplicate transaction (Exact same merchant, amount, and day)
        {
            "date": (datetime.now() - timedelta(days=22, hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "description": "Comcast Cable",
            "amount": 120.00,
            "category": "Utilities"
        },
        {
            "date": (datetime.now() - timedelta(days=22, hours=2, minutes=5)).strftime("%Y-%m-%d %H:%M:%S"),
            "description": "Comcast Cable",
            "amount": 120.00,
            "category": "Utilities"
        }
    ]
    
    test_data.extend(anomalies)
    test_data.sort(key=lambda x: x["date"])
    
    save_csv(
        "c:/Users/jatin/ragprojects/project_1/backend/data/transactions_test.csv",
        test_data,
        ["date", "description", "amount", "category"]
    )
    
    print("\nData generation complete! You have:")
    print("1. transactions_train.csv - For training models offline.")
    print("2. transactions_test.csv  - Containing 5 targeted anomalies to verify detection.")

if __name__ == "__main__":
    main()
