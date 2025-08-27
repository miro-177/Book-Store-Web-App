import mysql.connector

# Database connection
def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="pw",
        database="book_store"
    )

# Featured tab look up
def get_featured_books():
    db = connect_db()
    cursor = db.cursor(dictionary=True)
    query = """
    SELECT 
        b.*, 
        SUM(o.quantity) AS total_ordered_quantity
    FROM 
        book b
    JOIN 
        orderitems o ON b.isbn = o.isbn
    GROUP BY 
        b.isbn
    ORDER BY 
        total_ordered_quantity DESC;
    """
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
    db.close()
    return result

def get_coming_soon_books():
    db = connect_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM book WHERE quantity = 0;")
    result = cursor.fetchall()
    cursor.close()
    db.close()
    return result

def search_books(term):
    db = connect_db()
    cursor = db.cursor(dictionary=True)
    query = """
        SELECT * FROM book
    WHERE REPLACE(LOWER(author), '.', '') LIKE %s
       OR REPLACE(LOWER(title), '.', '') LIKE %s
       OR LOWER(category) LIKE %s
       OR isbn LIKE %s;
    """
    term = f"%{term}%"
    cursor.execute(query, (term, term, term, term))
    result = cursor.fetchall()
    cursor.close()
    db.close()
    return result
# Sample usage
if __name__ == "__main__":
    print("FEATURED BOOKS:")
    for book in get_featured_books():
        print(book)

    print("\nCOMING SOON:")
    for book in get_coming_soon_books():
        print(book)

    print("\nSEARCH RESULTS FOR 'JK':")
    for book in search_books("JK"):
        print(book)