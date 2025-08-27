from cryptography.fernet import Fernet
from datetime import datetime, timedelta, date
import mysql.connector
import random
import string

fernet_key = b'zmuYnQQtBzYyBZHuc9TxNpe6y6-IzBHyXwpvqV0Oa1o=' #stuff used for card encryption/ decryption
fernet = Fernet(fernet_key)


def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="DontHackMe!2",
        database="book_store"
    )

def fetch_one(query, params=None, dictionary=True):
    db = connect_db()
    cursor = db.cursor(dictionary=dictionary)
    cursor.execute(query, params or ())
    result = cursor.fetchone()
    cursor.close()
    db.close()
    return result

def fetch_all(query, params=None, dictionary=True):
    db = connect_db()
    cursor = db.cursor(dictionary=dictionary)
    cursor.execute(query, params or ())
    result = cursor.fetchall()
    cursor.close()
    db.close()
    return result

def encrypt_card_info(card_number: str) -> str:
    return fernet.encrypt(card_number.encode()).decode()

def decrypt_card_info(encrypted_card_number: str) -> str:
    return fernet.decrypt(encrypted_card_number.encode()).decode()




def execute_query(query, params=None, commit=False):
    db = connect_db()
    cursor = db.cursor()
    cursor.execute(query, params or ())
    if commit:
        db.commit()
    cursor.close()
    db.close()

def get_featured_books():
    return fetch_all("""
        SELECT b.*, SUM(o.quantity) AS total_ordered_quantity
        FROM book b
        JOIN orderitems o ON b.isbn = o.isbn
        GROUP BY b.isbn
        ORDER BY total_ordered_quantity DESC
        LIMIT 20
    """)

def get_coming_soon_books():
    return fetch_all("SELECT * FROM book WHERE quantity = 0 LIMIT 5")

def get_book_by_isbn(isbn):
    return fetch_one("SELECT * FROM book WHERE isbn = %s", (isbn,))


def login_attempt(name, hashed_password):
    return fetch_one("""
        SELECT * FROM user 
        WHERE (email = %s) AND password = %s
    """, (name, hashed_password))

def search_books(term, genre=None):
    like_term = f"%{term.lower().replace('.', '')}%"
    sql = """
        SELECT * FROM book
        WHERE (REPLACE(LOWER(title), '.', '') LIKE %s
           OR REPLACE(LOWER(author), '.', '') LIKE %s
           OR LOWER(category) LIKE %s
           OR isbn LIKE %s)
    """
    params = [like_term] * 4
    if genre:
        sql += " AND category = %s"
        params.append(genre)
    return fetch_all(sql, tuple(params))

def email_exists(email):
    return fetch_one("SELECT account_id FROM user WHERE email = %s", (email,))

def phone_exists(phone):
    return fetch_one("SELECT account_id FROM user WHERE phone_number = %s", (phone,))

def insert_user(name, phone, email, hashed_password, promos):
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO user (name, phone_number, email, password, promos)
        VALUES (%s, %s, %s, %s, %s)
    """, (name, phone, email, hashed_password, promos))
    db.commit()
    account_id = cursor.lastrowid
    cursor.close()
    db.close()
    return account_id

def insert_shipping_address(account_id, street, city, state, zip_code):
    execute_query("""
        INSERT INTO shippingaddress (account_id, street, city, state, zip)
        VALUES (%s, %s, %s, %s, %s)
    """, (account_id, street, city, state, zip_code), commit=True)

def get_payment_info(account_id):
    result = fetch_one("""
        SELECT payment_id, card_type, card_number,
               DATE_FORMAT(expiration_date, '%Y-%m') AS expiration_date
        FROM paymentinfo
        WHERE account_id = %s
    """, (account_id,))

    if result and result['card_number']:
        try:
            decrypted_card = decrypt_card_info(result['card_number'])
            result = dict(result)  
            result['card_number'] = decrypted_card
        except Exception as e:
            print("Decryption failed:", e)
            result['card_number'] = ''

    return result


def update_payment_info(account_id, cardtype, encrypted_cardnumber, expdate):
    full_exp = expdate + "-01"
    execute_query("""
        UPDATE paymentinfo
        SET card_type = %s,
            card_number = %s,
            expiration_date = %s
        WHERE account_id = %s
    """, (cardtype, encrypted_cardnumber, full_exp, account_id), commit=True)


def insert_payment_info(account_id, cardtype, encrypted_cardnumber, expdate):
    full_exp = expdate + "-01"
    execute_query("""
        INSERT INTO paymentinfo (account_id, card_type, card_number, expiration_date)
        VALUES (%s, %s, %s, %s)
    """, (account_id, cardtype, encrypted_cardnumber, full_exp), commit=True)

def insert_verification_token(account_id, token, expiration_time):
    execute_query("""
        INSERT INTO tokens (account_id, token, token_type, expiration_time)
        VALUES (%s, %s, %s, %s)
    """, (account_id, token, "EMAIL", expiration_time), commit=True)



def get_token_email(token):
    return fetch_one("""
        SELECT account_id, expiration_time FROM tokens
        WHERE token = %s AND token_type = %s
    """, (token, "EMAIL"))

def delete_token(token):
    execute_query("DELETE FROM tokens WHERE token = %s", (token,), commit=True)

def activate_user(account_id):
    execute_query("UPDATE user SET user_status = %s WHERE account_id = %s",
                  ("active", account_id), commit=True)



def get_user_cart(account_id):
    return fetch_all("""
        SELECT c.isbn, b.title, b.selling_price AS price, COUNT(*) AS quantity
        FROM Cart c
        JOIN Book b ON c.isbn = b.isbn
        WHERE c.account_id = %s
        GROUP BY c.isbn
    """, (account_id,))

def add_to_cart(account_id, isbn):
    execute_query("""
        INSERT INTO cart (account_id, isbn)
        VALUES (%s, %s)
    """, (account_id, isbn), commit=True)


def get_cart_items(account_id):
    return fetch_all("""
        SELECT c.isbn, b.title, b.selling_price, COUNT(*) AS quantity
        FROM cart c
        JOIN book b ON b.isbn = c.isbn
        WHERE c.account_id = %s
        GROUP BY c.isbn, b.title, b.selling_price
    """, (account_id,))

def remove_cart_item(account_id, isbn):
    execute_query("""
        DELETE FROM cart
        WHERE cart_item_id = (
            SELECT cart_item_id FROM (
                SELECT cart_item_id
                FROM cart
                WHERE account_id = %s AND isbn = %s
                LIMIT 1
            ) AS sub
        )
    """, (account_id, isbn), commit=True)


def update_user_profile(account_id, name, phone, email, password, promos):
    query = """
        UPDATE user SET name=%s, phone_number=%s, email=%s, password=%s, promos=%s
        WHERE account_id=%s
    """
    execute_query(query, (name, phone, email, password, promos, account_id), commit=True)

def get_shipping_address(account_id):
    return fetch_one("SELECT * FROM shippingaddress WHERE account_id = %s", (account_id,))

def update_shipping_address(account_id, street, city, state, zip_code):
    query = """
        UPDATE shippingaddress SET street=%s, city=%s, state=%s, zip=%s
        WHERE account_id=%s
    """
    execute_query(query, (street, city, state, zip_code, account_id), commit=True)

def insert_shipping_address(account_id, street, city, state, zip_code):
    query = """
        INSERT INTO shippingaddress (account_id, street, city, state, zip)
        VALUES (%s, %s, %s, %s, %s)
    """
    execute_query(query, (account_id, street, city, state, zip_code), commit=True)

def insert_payment_info(account_id, cardtype, cardnumber, expdate):
    encrypted = Fernet.encrypt(cardnumber.encode()).decode()
    full_exp = expdate + "-01"
    query = """
        INSERT INTO paymentinfo (account_id, card_type, card_number, expiration_date)
        VALUES (%s, %s, %s, %s)
    """
    execute_query(query, (account_id, cardtype, encrypted, full_exp), commit=True)

def id_lookup(account_id):
    return fetch_one("SELECT * FROM user WHERE account_id = %s", (account_id,))

def email_lookup(email):
    return fetch_one("SELECT account_id FROM user WHERE email = %s", (email,))

def insert_reset_token(account_id, token, expiration):
    query = """
        INSERT INTO tokens (account_id, token, token_type, expiration_time)
        VALUES (%s, %s, 'Password', %s)
    """
    execute_query(query, (account_id, token, expiration), commit=True)

def token_password(token):
    return fetch_one("""
        SELECT * FROM tokens
        WHERE token = %s AND token_type = 'Password' AND expiration_time > NOW()
    """, (token,))

def update_password(account_id, hashed_pw):
    execute_query("UPDATE user SET password = %s WHERE account_id = %s", (hashed_pw, account_id), commit=True)

def delete_token(token):
    execute_query("DELETE FROM tokens WHERE token = %s", (token,), commit=True)


def add_book(isbn, category, title, author, edition, publisher,
                publication_date, quantity, threshold,
                buying_price, selling_price, description):
    query = """
        INSERT INTO book (
            isbn, category, title, author, edition,
            publisher, publication_date, quantity,
            minimum_threshold, buying_price, selling_price, description
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        isbn, category, title, author, edition,
        publisher, publication_date, quantity,
        threshold, buying_price, selling_price, description
    )
    execute_query(query, values, commit=True)


def create_promotion(promo_code, percent, start_date, end_date):
    query = """
        INSERT INTO promotions (promo_code, percent, start_date, end_date, emailed)
        VALUES (%s, %s, %s, %s, %s)
    """
    execute_query(query, (promo_code, percent, start_date, end_date, 0), commit=True)

def get_valid_promo(promo_code):
    today = date.today()
    return fetch_one("""
        SELECT percent
        FROM promotions
        WHERE promo_code = %s
          AND start_date <= %s
          AND end_date >= %s
    """, (promo_code.upper(), today, today))

def generate_confirmation_code(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def insert_order(account_id, address_id, payment_id, promo_code=None):
    confirmation_num = generate_confirmation_code()
    order_status = 'Pending'

    db = connect_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO orders (
            account_id, time_placed, order_status,
            address_id, payment_id, promo_code, confirmation_num
        )
        VALUES (%s, NOW(), %s, %s, %s, %s, %s)
    """, (
        account_id,
        order_status,
        address_id,
        payment_id,
        promo_code if promo_code else None,
        confirmation_num
    ))
    db.commit()

    cursor.execute("SELECT LAST_INSERT_ID() AS order_id")
    order_id = cursor.fetchone()[0]

    cursor.close()
    db.close()

    return order_id, confirmation_num


def insert_order_item(order_id, isbn, quantity, user_price):
    execute_query("""
        INSERT INTO orderitems (order_id, isbn, quantity, user_price)
        VALUES (%s, %s, %s, %s)
    """, (order_id, isbn, quantity, user_price), commit=True)

def clear_cart(account_id):
    print(f"Clearing cart for account_id={account_id}")
    execute_query("DELETE FROM cart WHERE account_id = %s", (account_id,), commit=True)
    print("Cart cleared")


def get_user_orders(account_id):
    orders = fetch_all("""
        SELECT order_id, time_placed, confirmation_num, promo_code
        FROM orders
        WHERE account_id = %s
        ORDER BY time_placed DESC
    """, (account_id,))

    for order in orders:
        items = fetch_all("""
            SELECT oi.isbn, oi.quantity, oi.user_price, b.title
            FROM orderitems oi
            JOIN book b ON oi.isbn = b.isbn
            WHERE oi.order_id = %s
        """, (order['order_id'],))

        order['items'] = items
        order['total'] = round(sum(i['user_price'] * i['quantity'] for i in items), 2)
        order['formatted_date'] = order['time_placed'].strftime("%B %d, %Y")

    return orders

def reorder_order_items(account_id, order_id):
    items = fetch_all("""
        SELECT isbn
        FROM orderitems
        WHERE order_id = %s
    """, (order_id,))

    print(f"Reordering {len(items)} items for account {account_id} from order {order_id}")

    for item in items:
        print(f"Inserting ISBN {item['isbn']} into cart for account {account_id}")
        execute_query("""
            INSERT INTO cart (account_id, isbn)
            VALUES (%s, %s)
        """, (account_id, item['isbn']),commit=True)
