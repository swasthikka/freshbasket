from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL

import pymysql
pymysql.install_as_MySQLdb()

app = Flask(__name__)

# Flask app secret key for session management
app.secret_key = 'your_secret_key'

# Database configuration for MySQL RDS
app.config['MYSQL_HOST'] = 'database-1.cp8wmwwqwyoo.us-east-1.rds.amazonaws.com'
app.config['MYSQL_USER'] = 'admin'
app.config['MYSQL_PASSWORD'] = 'Swas_1234'
app.config['MYSQL_DB'] = 'fresh'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Initialize MySQL
mysql = MySQL(app)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Validate input and insert into the database
        if not username or not email or not password:
            flash('Please fill out all fields.', 'danger')
            return redirect(url_for('register'))

        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)',
                       (username, email, password))
        mysql.connection.commit()
        cursor.close()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s', (email, password))
        user = cursor.fetchone()

        if user:
            session['loggedin'] = True
            session['id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('shop'))
        else:
            flash('Incorrect email or password!', 'danger')
        cursor.close()
    return render_template('login.html')

@app.route('/shop', methods=['GET'])
def shop():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM items')
        items = cursor.fetchall()
        cursor.close()
        return render_template('shop.html', items=items)
    else:
        flash('Please log in to access the shop.', 'warning')
        return redirect(url_for('login'))

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'loggedin' in session:
        item_id = request.form['item_id']
        if 'cart' not in session:
            session['cart'] = []
        session['cart'].append(item_id)
        flash('Item added to cart!', 'success')
        return redirect(url_for('shop'))
    else:
        flash('Please log in to add items to your cart.', 'warning')
        return redirect(url_for('login'))

@app.route('/items', methods=['GET', 'POST'])
def items():
    cursor = mysql.connection.cursor()
    if request.method == 'POST':
        item_name = request.form['item_name']
        price = request.form['price']
        stock = request.form['stock']
        cursor.execute('INSERT INTO items (item_name, price, stock) VALUES (%s, %s, %s)',
                       (item_name, price, stock))
        mysql.connection.commit()
        flash('Item added successfully!', 'success')
    cursor.execute('SELECT * FROM items')
    items = cursor.fetchall()
    cursor.close()
    return render_template('items.html', items=items)

@app.route('/place_order', methods=['POST'])
def place_order():
    if 'loggedin' in session:
        try:
            user_id = session['id']
            cursor = mysql.connection.cursor()
            cursor.execute('INSERT INTO orders (user_id, status) VALUES (%s, %s)', (user_id, 'Pending'))
            order_id = cursor.lastrowid
            for item_id in session.get('cart', []):
                cursor.execute('INSERT INTO order_items (order_id, item_id) VALUES (%s, %s)', (order_id, item_id))
            mysql.connection.commit()
            session.pop('cart', None)
            flash('Order placed successfully!', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error placing order: {str(e)}', 'danger')
        finally:
            cursor.close()
        return redirect(url_for('user_dashboard'))
    else:
        flash('Please log in to place an order.', 'warning')
        return redirect(url_for('login'))

@app.route('/user_dashboard')
def user_dashboard():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor()
        cursor.execute('''
            SELECT orders.id AS order_id, GROUP_CONCAT(items.item_name) AS items, orders.status 
            FROM orders
            JOIN order_items ON orders.id = order_items.order_id
            JOIN items ON order_items.item_id = items.id
            WHERE orders.user_id = %s
            GROUP BY orders.id
        ''', (session['id'],))
        orders = cursor.fetchall()
        cursor.close()
        return render_template('user_dashboard.html', orders=orders)
    else:
        flash('Please log in to view your dashboard.', 'warning')
        return redirect(url_for('login'))

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if request.method == 'POST':
        order_id = request.form['order_id']
        status = request.form['status']
        cursor = mysql.connection.cursor()
        cursor.execute('UPDATE orders SET status = %s WHERE id = %s', (status, order_id))
        mysql.connection.commit()
        flash('Order status updated!', 'success')
        cursor.close()
    cursor = mysql.connection.cursor()
    cursor.execute('''
        SELECT orders.id AS order_id, GROUP_CONCAT(items.item_name) AS items, orders.status 
        FROM orders
        JOIN order_items ON orders.id = order_items.order_id
        JOIN items ON order_items.item_id = items.id
        GROUP BY orders.id
    ''')
    orders = cursor.fetchall()
    cursor.close()
    return render_template('admin_dashboard.html', orders=orders)

if __name__ == '__main__':
    app.run(debug=True)
