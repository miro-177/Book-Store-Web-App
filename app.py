from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash,make_response
from flask_mail import Mail, Message
import hashlib, secrets, os
from cryptography.fernet import Fernet
from datetime import datetime, timedelta, date

import sql_stuff
from sql_stuff import *


app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'software.engineering.team8@gmail.com'
app.config['MAIL_PASSWORD'] = 'mjwwvfrakxgpgrzl'  #Gmail app password

mail = Mail(app)
fernet_key = b'zmuYnQQtBzYyBZHuc9TxNpe6y6-IzBHyXwpvqV0Oa1o=' #stuff used for card encryption/ decryption
fernet = Fernet(fernet_key)
app.secret_key = "secret-key"

@app.context_processor
def inject_user_logged_in():
    return dict(user_logged_in = 'user_id' in session)

@app.route("/")
def homepage():
    user_logged_in = 'user_id' in session
    user_name = None
    user = None

    if user_logged_in:
        user = id_lookup(session['user_id'])
        if user:
            user_name = (user.get('name') or user.get('email')).split()[0].split('@')[0]

    featured_books = get_featured_books()
    coming_soon_books = get_coming_soon_books()

    return render_template("index.html", featured=featured_books, coming_soon=coming_soon_books, user_logged_in=user_logged_in, user_name=user_name)

@app.route("/book/<isbn>")
def bookpage(isbn):
    book = get_book_by_isbn(isbn)
    return render_template("bookpage.html", book=book) if book else ("Book not found", 404)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form["name"]
        password = hashlib.sha256(request.form["password"].encode()).hexdigest()

        user = login_attempt(name, password)
        if user:
            session.update({
                "user_id": user["account_id"],
                "email": user["email"],
                "phone_number": user["phone_number"],
                "user_status": user["user_status"],
                "is_admin": user["user_status"].lower() == "admin"
            })
            return redirect(url_for("admin" if user["user_status"] == "Admin" else "homepage"))
        return render_template("loginpage.html", error="Invalid credentials")

    return render_template("loginpage.html")


@app.route("/search")
def search():
    term = request.args.get("q", "")
    genre = request.args.get("genre", "")
    results = search_books(term, genre)
    return render_template("searchpage.html", results=results, query=term, genre=genre)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phonenumber")
        email = request.form.get("email")
        password = request.form.get("password")
        street = request.form.get("street")
        city = request.form.get("city")
        state = request.form.get("state")
        zip_code = request.form.get("zip")
        cardtype = request.form.get("cardtype")
        cardnumber = request.form.get("cardnumber")
        expdate = request.form.get("expdate")
        promos = 1 if request.form.get("promos") == "1" else 0

        if not all([name, phone, email, password]):
            return render_template("registration.html", error="Missing required fields.")

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        if email_exists(email):
            return render_template("registration.html", error="An account with this email already exists.")
        if phone_exists(phone):
            return render_template("registration.html", error="An account with this phone number already exists.")

        try:
            account_id = insert_user(name, phone, email, hashed_password, promos)

            if any([street, city, state, zip_code]):
                insert_shipping_address(account_id, street, city, state, zip_code)

            if cardtype and cardnumber and expdate:
                try:
                    encrypted_cardnumber = fernet.encrypt(cardnumber.encode()).decode()
                    insert_payment_info(account_id, cardtype, encrypted_cardnumber, expdate)
                except Exception:
                    return render_template("registration.html", error="Invalid payment info.")

            token_value = secrets.token_urlsafe(32)
            expiration_time = (datetime.utcnow() + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
            insert_verification_token(account_id, token_value, expiration_time)

            verification_link = url_for("verify_email", token=token_value, _external=True)
            msg = Message(
                subject="Verify Your Email",
                sender=app.config['MAIL_USERNAME'],
                recipients=[email],
                body=f"""
                    Hi {name},

                    Thanks for registering! Please verify your email by clicking this link:

                    {verification_link}

                    This link will expire in 3 hours.

                    If you did not register, you can ignore this email.
                    """
            )
            try:
                mail.send(msg)
            except Exception as e:
                print("Failed to send verification email:", e)

            return redirect(url_for("registrationconfirmation"))

        except Exception as e:
            print("Unexpected registration error:", e)
            return render_template("registration.html", error=f"An unexpected error occurred: {str(e)}")

    return render_template("registration.html")


@app.route("/verifyemail/<token>")
def verify_email(token):
    try:
        token_record = get_token_email(token)

        if not token_record:
            flash("Invalid or expired verification link.", "error")
            return redirect(url_for("homepage"))

        if token_record["expiration_time"] < datetime.utcnow():
            delete_token(token)
            flash("Verification link has expired.", "error")
            return redirect(url_for("homepage"))

        activate_user(token_record["account_id"])
        delete_token(token)

        flash("Your account has been successfully verified!", "success")
        return redirect(url_for("homepage"))

    except Exception as e:
        print("Verification error:", e)
        flash(f"Verification failed: {str(e)}", "error")
        return redirect(url_for("homepage"))

@app.route("/shoppingcart")
def shoppingcart():
    return render_template("shoppingcart.html")

@app.route("/api/cart/add", methods=["POST"])
def api_add_to_cart():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    isbn = data.get("isbn")

    if not isbn:
        return jsonify({"error": "ISBN required"}), 400

    add_to_cart(session["user_id"], isbn)
    return jsonify({"success": True})


@app.route("/api/cart/remove", methods=["POST"])
def api_remove_from_cart():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    isbn = data.get("isbn")

    if not isbn:
        return jsonify({"error": "ISBN required"}), 400

    remove_cart_item(session["user_id"], isbn)
    return jsonify({"success": True})


@app.route("/api/cart", methods=["GET"])
def api_get_cart():
    if "user_id" not in session:
        return jsonify({})

    rows = get_cart_items(session["user_id"])

    return jsonify({
        row["isbn"]: {
            "title": row["title"],
            "price": float(row["selling_price"]),
            "quantity": row["quantity"]
        } for row in rows
    })



@app.route("/registrationconfirmation")
def registrationconfirmation():
    return render_template("registrationconfirm.html")

@app.route("/orderhistory")
def orderhistory():
    if "user_id" not in session:
        return redirect(url_for("login"))

    account_id = session["user_id"]
    orders = sql_stuff.get_user_orders(account_id)

    return render_template("orderhistory.html", orders=orders)


@app.route("/reorder", methods=["POST"])
def reorder():
    if "user_id" not in session:
        flash("Please log in to reorder.", "error")
        return redirect(url_for("login"))

    account_id = session["user_id"]
    order_id = request.form.get("order_id")

    if not order_id:
        flash("No order specified.", "error")
        return redirect(url_for("orderhistory"))

    try:
        # Call a function that copies order items to the cart in DB for the user
        sql_stuff.reorder_order_items(account_id, order_id)
        flash("Order items added to your cart.", "success")
    except Exception as e:
        print("Reorder error:", e)
        flash("Failed to reorder items. Please try again.", "error")

    return redirect(url_for("orderhistory"))


@app.route("/editprofile", methods=["GET", "POST"])
def editprofile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    account_id = session["user_id"]

    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phonenumber"]
        email = request.form["email"]
        password = request.form["password"]
        street = request.form["street"]
        city = request.form["city"]
        state = request.form["state"]
        zip_code = request.form["zip"]
        cardtype = request.form.get("cardtype")
        cardnumber = request.form.get("cardnumber")
        expdate = request.form.get("expdate")
        promos = 1 if request.form.get("promos") == "1" else 0

        sql_stuff.update_user_profile(account_id, name, phone, email, password, promos)

        shipping = sql_stuff.get_shipping_address(account_id)
        if shipping:
            sql_stuff.update_shipping_address(account_id, street, city, state, zip_code)
        else:
            sql_stuff.insert_shipping_address(account_id, street, city, state, zip_code)

        if cardtype and cardnumber and expdate:
            if cardtype and cardnumber and expdate:
                encrypted_cardnumber = encrypt_card_info(cardnumber)
                existing_payment = sql_stuff.get_payment_info(account_id)
                user = sql_stuff.id_lookup(account_id)
                try:
                    if existing_payment:
                        sql_stuff.update_payment_info(account_id, cardtype, encrypted_cardnumber, expdate)
                    else:
                        sql_stuff.insert_payment_info(account_id, cardtype, encrypted_cardnumber, expdate)
                except Exception as e:
                    print("Payment error:", e)
                    return render_template("editprofilepage.html", user=user, shipping=shipping,
                                           error="Invalid payment info.")

    user = sql_stuff.id_lookup(account_id)
    shipping = sql_stuff.get_shipping_address(account_id)
    payment = sql_stuff.get_payment_info(account_id)

    return render_template("editprofilepage.html", user=user, shipping=shipping, payment=payment)

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if "user_id" not in session:
        return redirect(url_for("login"))

    account_id = session["user_id"]
    user = sql_stuff.id_lookup(account_id)
    shipping = sql_stuff.get_shipping_address(account_id)
    payment = sql_stuff.get_payment_info(account_id)
    cart_items = sql_stuff.get_cart_items(account_id)

    subtotal = sum(item['selling_price'] * item['quantity'] for item in cart_items)
    total = subtotal
    discount = 0
    discount_reason = None
    promo_code = ""

    if request.method == "POST":
        if "apply_coupon" in request.form:
            action = "apply_coupon"
        elif "complete_purchase" in request.form:
            action = "complete_purchase"
        else:
            action = None
        promo_code = request.form.get("promo_code", "").strip()
        email = request.form.get("email") or user.get("email")  # fallback to DB email
        first_name = user.get("first_name", "Customer")

        promo = sql_stuff.get_valid_promo(promo_code) if promo_code else None
        if promo:
            discount = round(subtotal * (promo["percent"] / 100), 2)
            discount_reason = f"{promo['percent']}% discount applied"
        elif promo_code:
            discount_reason = "Invalid or expired promo code"
            flash(discount_reason, "error")

        total = round(subtotal - discount, 2)

        if action == "apply_coupon":
            return render_template("checkout.html",
                                   user=user, shipping=shipping, payment=payment,
                                   cart_items=cart_items, subtotal=subtotal,
                                   discount=discount, discount_reason=discount_reason,
                                   promo_code=promo_code, total=total)

        elif action == "complete_purchase":
            try:

                order_id, confirmation_num = sql_stuff.insert_order(
                    account_id,
                    shipping["address_id"],
                    payment["payment_id"],
                    promo_code if discount else None
                )
                for item in cart_items:
                    sql_stuff.insert_order_item(
                        order_id,
                        item["isbn"],
                        item["quantity"],
                        item["selling_price"]
                    )

                sql_stuff.clear_cart(account_id)

                msg = Message(
                    subject="Your Bookstore Order Confirmation",
                    sender=app.config['MAIL_USERNAME'],
                    recipients=[email],
                    body=f"Hi {first_name},\n\nThank you for your order! Your books will be shipped soon. The confirmation code is {confirmation_num}.\n\n- Bookstore Team"
                )
                mail.send(msg)

            except Exception as e:
                print("Error completing order:", e)
                return "Something went wrong with your order", 500
            response = render_template("orderconfirmationpage.html", confirmation_code=confirmation_num)
            resp = make_response(response)
            resp.set_cookie('clear_cart', '1', max_age=10)
            return resp

    # Initial GET request
    return render_template("checkout.html",
                           user=user, shipping=shipping, payment=payment,
                           cart_items=cart_items, subtotal=subtotal,
                           discount=discount, discount_reason=discount_reason,
                           promo_code=promo_code,total=total)



@app.route("/order-confirmation")
def order_confirmation():
    return render_template("orderconfirmationpage.html")



@app.route("/forgotpassword", methods=["GET", "POST"])
def forgotpassword():
    if request.method == "POST":
        email = request.form.get("name")
        user = sql_stuff.email_lookup(email)
        if not user:
            return render_template("forgotpassword.html", error="No account found.")

        token = secrets.token_urlsafe(32)
        exp = datetime.utcnow() + timedelta(hours=3)
        sql_stuff.insert_reset_token(user["account_id"], token, exp.strftime('%Y-%m-%d %H:%M:%S'))

        reset_link = url_for("resetpassword", token=token, _external=True)
        msg = Message(
            subject="Password Reset Request",
            sender=app.config['MAIL_USERNAME'],
            recipients=[email],
            body=f"Reset your password:\n\n{reset_link}"
        )
        try:
            mail.send(msg)
            flash("Password reset link sent.")
        except Exception as e:
            print(f"Email error: {e}")
            flash("Failed to send reset email.", "error")

        return redirect(url_for("login"))

    return render_template("forgotpassword.html")

@app.route("/resetpassword/<token>", methods=["GET"])
def resetpassword(token):
    token_row = sql_stuff.token_password(token)
    if not token_row:
        flash("Invalid or expired token.", "error")
        return redirect(url_for("login"))

    return render_template("resetpassword.html", token=token)

@app.route("/setnewpassword", methods=["POST"])
def setnewpassword():
    new_pw = request.form.get("new_password")
    confirm_pw = request.form.get("confirm_password")
    token = request.form.get("token")

    if new_pw != confirm_pw:
        return render_template("resetpassword.html", token=token, error="Passwords do not match.")

    token_row = sql_stuff.token_password(token)
    if not token_row:
        return render_template("resetpassword.html", token=token, error="Invalid or expired token.")

    hashed = hashlib.sha256(new_pw.encode()).hexdigest()
    sql_stuff.update_password(token_row["account_id"], hashed)
    sql_stuff.delete_token(token)

    flash("Password reset successful.")
    return redirect(url_for("login"))


@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/orderconfirmation")
def orderconfirmation():
    return render_template("orderconfirmationpage.html")

@app.route("/managebooks", methods=["GET", "POST"])
def managebooks():
    if request.method == "POST":
        isbn = request.form.get("isbn")
        title = request.form.get("title")
        author = request.form.get("authors")
        category = request.form.get("category")
        edition = request.form.get("edition")
        publisher = request.form.get("publisher")
        publication_date = request.form.get("expdate")
        quantity = int(request.form.get("quantity_in_stock"))
        threshold = int(request.form.get("minimum_threshold"))
        buying_price = float(request.form.get("buying_price"))
        selling_price = float(request.form.get("selling_price"))
        description = request.form.get("description")

        cover = request.files.get("cover_picture")
        cover_path = None

        if cover and cover.filename != "":
            ext = os.path.splitext(cover.filename)[1]
            filename = f"{isbn}{ext}"
            os.makedirs("static/covers", exist_ok=True)
            cover_path = os.path.join("static", "covers", filename)
            cover.save(cover_path)

        try:
            add_book(isbn, category, title, author, edition, publisher,
                        publication_date, quantity, threshold, buying_price,
                        selling_price, description)
            flash("Book added successfully!", "success")
        except Exception as err:
            import traceback
            traceback.print_exc()
            flash(f"Database error: {err}", "danger")

        return redirect(url_for("managebooks"))

    return render_template("managebooks.html")


@app.route("/manageusers")
def manageusers():
    return render_template("manageusers.html")


@app.route("/managepromotions", methods=["GET", "POST"])
def managepromotions():
    if request.method == "POST":
        try:
            promo_code = request.form["promo_code"]
            start_date = request.form["start_date"]
            end_date = request.form["end_date"]
            percent = float(request.form["discount_percentage"])

            create_promotion(promo_code, percent, start_date, end_date)
            flash("Promotion created successfully!", "success")
            return redirect(url_for("managepromotions"))

        except Exception as e:
            print("Error creating the promotion:", e)
            flash("An error occurred while creating the promotion.", "error")

    return render_template("managepromotions.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("homepage"))



if __name__ == "__main__":
    app.run(debug=True)
