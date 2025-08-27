# Online Bookstore UI

UI and backend for an online bookstore system using Flask and MySQL.

    
## Prerequisites

- Python 3.10+
- MySQL Server (with a database named `book_store` and appropriate tables)
- pip (Python package manager)

## Setup Instructions

1. **Download the repository**:

   -Download the repository 

2. **Install Python dependencies:**

   ```sh
   pip install flask
   pip install flask mysql-connector-python
   ```

3. **Set up the MySQL database:**

   - Ensure MySQL server is running.
   - Switch to use of "book_store" database and proceed

   Example:
   ```sh
   mysql -u root -p < path/to/BookStore_Database.sql
   ```

   - Update the `connect_db()` function in `app.py` with your MySQL username and password if needed.

4. **Run the Flask app:**

   ```sh
   python app.py
   ```

5. **Open your browser and go to:**

   ```
   http://127.0.0.1:5000/
   ```

## Project Structure

- `app.py` - Main Flask application.
- `templates/` - HTML templates (Jinja2).
- `static/` - Static files (CSS, images, JS).
- `README.md` - This file.
