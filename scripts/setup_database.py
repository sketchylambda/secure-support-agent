import sqlite3
import pandas as pd
import os

DB_FILE = "data/ecommerce.db"
CSV_FILE = "data/Bitext_Sample_Customer_Service_Training_Dataset.csv"

def setup_mock_orders(conn):
    """Creates the orders table with mock customer data."""
    print("📦 Setting up 'orders' table...")
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer_name TEXT,
            status TEXT,
            shipping_address TEXT
        )
    ''')

    mock_data = [
        ('ORD-123', 'Alice Smith', 'Shipped', '123 Apple St, NY'),
        ('ORD-456', 'Bob Jones', 'Processing', '456 Banana Ave, CA'),
        ('ORD-789', 'Charlie Brown', 'Delivered', '789 Cherry Ln, TX')
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO orders VALUES (?, ?, ?, ?)', mock_data)
    conn.commit()
    print(f"✅ Inserted {len(mock_data)} mock orders.")

def setup_knowledge_base(conn):
    """Loads the Kaggle CSV into the support_knowledge table."""
    print("\n📚 Setting up 'support_knowledge' table from Kaggle CSV...")
    
    if not os.path.exists(CSV_FILE):
        print(f"❌ Error: Could not find the dataset at {CSV_FILE}")
        print("Please download it from Kaggle and place it in the data/ folder.")
        return

    try:
        df = pd.read_csv(CSV_FILE)
        # Clean up column names
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        # Write to SQLite
        df.to_sql('support_knowledge', conn, if_exists='replace', index=False)
        print(f"✅ Successfully loaded {len(df)} knowledge base records.")
        
    except Exception as e:
        print(f"❌ Error loading CSV: {str(e)}")

def main():
    # Ensure the data directory exists
    os.makedirs("data", exist_ok=True)
    
    print(f"Initializing database at {DB_FILE}...\n")
    conn = sqlite3.connect(DB_FILE)
    
    try:
        setup_mock_orders(conn)
        setup_knowledge_base(conn)
        print("\n🎉 Database setup complete! Your agent is ready to run.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()