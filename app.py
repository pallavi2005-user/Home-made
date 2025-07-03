from flask import Flask, render_template, request, redirect, url_for, session, flash
import boto3
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# AWS Configuration
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
user_table = dynamodb.Table('Users')
orders_table = dynamodb.Table('Orders')

# Email Configuration
EMAIL_ADDRESS = 'kranthipallavi32@gmail.com'
EMAIL_PASSWORD = 'your_app_password_here'  # Replace with your actual Gmail App Password

# Product Data - Unchanged
veg_items = [
    {"name": "Mango Pickles", "price": 150, "img": "Mango-Pickles.jpg"},
    {"name": "Lemon Pickles", "price": 120, "img": "Lemon Pickles.jpg"},
    {"name": "Tomato Pickles", "price": 180, "img": "Tomato Pickles.jpg"},
    {"name": "Spicy Pandu Mirchi Pickles", "price": 160, "img": "Spicy Pandu Mirchi Pickles.jpg"},
    {"name": "Kakarakaya Pickles", "price": 170, "img": "Kakarakaya Pickles.jpg"}
]

non_veg_items = [
    {"name": "Gongura Chicken Pickles", "price": 300, "img": "Gongura Chicken Pickles.jpg"},
    {"name": "Mutton Pickles", "price": 350, "img": "Mutton Pickles.jpg"},
    {"name": "Fish Pickles", "price": 320, "img": "Fish Pickles.jpg"},
    {"name": "Gongura Prawns Pickles", "price": 340, "img": "Gongura Prawns Pickles.jpg"},
    {"name": "Gongura Mutton Pickles", "price": 360, "img": "Gongura Mutton Pickles.jpg"}
]

snack_items = [
    {"name": "Crispy Aam Papad", "price": 200, "img": "Crispy Aam Papad.jpg"},
    {"name": "Crispy Chekka Pakodi", "price": 100, "img": "Crispy Chekka Pakodi.jpg"},
    {"name": "Dryfruitladdu", "price": 120, "img": "Dryfruitladdu.jpg"},
    {"name": "Chekkalu", "price": 130, "img": "Chekkalu.jpg"},
    {"name": "Banana Chips", "price": 140, "img": "Banana chips.jpg"},
    {"name": "Boondhi Acchu", "price": 110, "img": "Boondhi acchu.jpg"},
    {"name": "Gavvalu", "price": 115, "img": "Gavvalu.jpg"},
    {"name": "Kaju Chikki", "price": 160, "img": "Kaju Chikki.jpg"},
    {"name": "Ragi Laddu", "price": 125, "img": "Ragi Laddu.jpg"}
]

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/veg-pickles')
def veg_pickles():
    return render_template('veg_pickles.html', items=veg_items)

@app.route('/non-veg-pickles')
def non_veg_pickles():
    return render_template('non_veg_pickles.html', items=non_veg_items)

@app.route('/snacks')
def snacks():
    return render_template('snacks.html', items=snack_items)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    item = request.form.to_dict()
    cart = session.get('cart', [])
    cart.append(item)
    session['cart'] = cart
    return redirect(request.referrer)

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    index = int(request.form['index'])
    cart = session.get('cart', [])
    if 0 <= index < len(cart):
        cart.pop(index)
    session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    cart_items = session.get('cart', [])
    total = sum(int(i['price']) for i in cart_items)
    return render_template('cart.html', cart=cart_items, total=total)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        name = request.form['fullname']
        email = request.form['email']
        address = request.form['address']
        phone = request.form['phone']
        payment = request.form['payment']
        cart_items = session.get('cart', [])
        total = sum(int(i['price']) for i in cart_items)
        order_id = str(uuid.uuid4())

        orders_table.put_item(Item={
            'order_id': order_id,
            'name': name,
            'email': email,
            'address': address,
            'phone': phone,
            'payment': payment,
            'total': total,
            'items': cart_items
        })

        send_email(email, "Order Confirmation", f"Thank you {name} for your order! Total: ₹{total}")

        session.pop('cart', None)
        return render_template('success.html', name=name, order_id=order_id)

    return render_template('checkout.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        return redirect(url_for('success'))
    return render_template('contact.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = user_table.get_item(Key={'email': email}).get('Item')
        if user and user['password'] == password:
            session['user'] = email
            flash("Login successful!", "success")
            return redirect(url_for('index'))
        flash("Invalid credentials", "danger")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_table.put_item(Item={'email': email, 'password': password})
        send_email(email, "Welcome to Pickle Paradise", "Thank you for signing up!")
        flash("Signup successful! Please login.", "success")
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

# Email Sending Function
def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == '__main__':
    app.run(debug=True)