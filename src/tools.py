import sqlite3

def get_order_details(order_id: str) -> str:
    """Fetches the order status, shipping address, and customer name for a given order ID."""
    try:
        conn = sqlite3.connect('data/ecommerce.db') 
        cursor = conn.cursor()
        
        cursor.execute("SELECT customer_name, status, shipping_address FROM orders WHERE order_id = ?", (order_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            name, status, address = result
            return f"Customer Name: {name}, Order Status: {status}, Shipping Address: {address}"
        else:
            return f"Order ID {order_id} not found in the database."
            
    except Exception as e:
        print(f"🚨 TOOL ERROR: {str(e)}")
        return f"Database error: {str(e)}"

def query_knowledge_base(search_term: str) -> str:
    """Searches past customer support logs for relevant intents.
    
    Args:
        search_term: A keyword to search for (e.g., 'refund', 'password')
    """
    try:
        conn = sqlite3.connect('data/ecommerce.db')
        cursor = conn.cursor()
        
        # Search the utterance column for the keyword
        query = """
            SELECT utterance, intent 
            FROM support_knowledge 
            WHERE utterance LIKE ? 
            LIMIT 5
        """
        cursor.execute(query, (f'%{search_term}%',))
        results = cursor.fetchall()
        conn.close()
        
        if results:
            formatted_results = "\n".join([f"Q: {r[0]} | Intent: {r[1]}" for r in results])
            return f"Found relevant past tickets:\n{formatted_results}"
        return f"No records found for '{search_term}'."
        
    except Exception as e:
        # If the table doesn't exist yet, give a helpful error
        if "no such table" in str(e).lower():
            return "Knowledge base not initialized. Please run scripts/setup_database.py first."
        return f"Database error: {str(e)}"