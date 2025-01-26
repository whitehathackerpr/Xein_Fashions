from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_mysqldb import MySQL
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from config import Config
import MySQLdb.cursors
import re
from decimal import Decimal
import os
from werkzeug.utils import secure_filename
import time
from flask_paginate import Pagination, get_page_parameter

app = Flask(__name__)
app.config.from_object(Config)

# Initialize MySQL
mysql = MySQL(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize Bcrypt
bcrypt = Bcrypt(app)

# User class
class User(UserMixin):
    def __init__(self, user_id, username, email, created_at=None):
        self.id = user_id
        self.username = username
        self.email = email
        self.created_at = created_at

@login_manager.user_loader
def load_user(user_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    
    if user:
        return User(user['id'], user['username'], user['email'], user['created_at'])
    return None

# Routes
@app.route('/')
def home():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM products ORDER BY created_at DESC LIMIT 8')
    products = cursor.fetchall()
    cursor.close()
    return render_template('home.html', products=products)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()
        
        if user and bcrypt.check_password_hash(user['password'], password):
            user_obj = User(user['id'], user['username'], user['email'], user['created_at'])
            login_user(user_obj)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        
        flash('Invalid email or password!', 'error')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Check if email already exists
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        if cursor.fetchone():
            flash('Email already exists!', 'error')
            return redirect(url_for('signup'))
        
        # Hash password and insert user
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        cursor.execute('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)',
                      (username, email, hashed_password))
        mysql.connection.commit()
        cursor.close()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/cart')
@login_required
def cart():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get cart items with product details
    cursor.execute('''
        SELECT ci.*, p.name, p.price, p.image 
        FROM cart_items ci 
        JOIN products p ON ci.product_id = p.id 
        WHERE ci.user_id = %s
    ''', (current_user.id,))
    
    cart_items = cursor.fetchall()
    
    # Calculate total
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    
    cursor.close()
    return render_template('cart.html', cart_items=cart_items, total=total)

# Add to cart route
@app.route('/add-to-cart', methods=['POST'])
@login_required
def add_to_cart():
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Check if product exists and has stock
    cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
    product = cursor.fetchone()
    
    if not product:
        cursor.close()
        return jsonify({'success': False, 'message': 'Product not found'})
    
    if product['stock'] < quantity:
        cursor.close()
        return jsonify({'success': False, 'message': 'Not enough stock'})
    
    # Check if item already in cart
    cursor.execute('SELECT * FROM cart_items WHERE user_id = %s AND product_id = %s',
                  (current_user.id, product_id))
    cart_item = cursor.fetchone()
    
    try:
        if cart_item:
            # Update quantity if already in cart
            new_quantity = cart_item['quantity'] + quantity
            if new_quantity > product['stock']:
                cursor.close()
                return jsonify({'success': False, 'message': 'Not enough stock'})
                
            cursor.execute('''
                UPDATE cart_items 
                SET quantity = quantity + %s 
                WHERE user_id = %s AND product_id = %s
            ''', (quantity, current_user.id, product_id))
        else:
            # Add new item to cart
            cursor.execute('''
                INSERT INTO cart_items (user_id, product_id, quantity) 
                VALUES (%s, %s, %s)
            ''', (current_user.id, product_id, quantity))
        
        mysql.connection.commit()
        
        # Get updated cart count
        cursor.execute('SELECT SUM(quantity) as count FROM cart_items WHERE user_id = %s',
                      (current_user.id,))
        cart_count = cursor.fetchone()['count'] or 0
        
        cursor.close()
        return jsonify({
            'success': True,
            'message': 'Product added to cart successfully',
            'cart_count': cart_count
        })
        
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'success': False, 'message': 'Error adding to cart'})

# Update cart quantity route
@app.route('/update-cart', methods=['POST'])
@login_required
def update_cart():
    data = request.get_json()
    item_id = data.get('item_id')
    change = data.get('change')
    
    cursor = mysql.connection.cursor()
    
    # Update quantity, ensuring it doesn't go below 1
    cursor.execute('''
        UPDATE cart_items 
        SET quantity = GREATEST(1, quantity + %s)
        WHERE id = %s AND user_id = %s
    ''', (change, item_id, current_user.id))
    
    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True})

# Remove from cart route
@app.route('/remove-from-cart', methods=['POST'])
@login_required
def remove_from_cart():
    data = request.get_json()
    item_id = data.get('item_id')
    
    cursor = mysql.connection.cursor()
    cursor.execute('DELETE FROM cart_items WHERE id = %s AND user_id = %s',
                  (item_id, current_user.id))
    
    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True})

# Helper function to get cart count (can be used in layout.html)
def get_cart_count():
    if current_user.is_authenticated:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT SUM(quantity) as count FROM cart_items WHERE user_id = %s',
                      (current_user.id,))
        result = cursor.fetchone()
        cursor.close()
        return result['count'] or 0
    return 0

# Add this to your context processors
@app.context_processor
def utility_processor():
    return {'get_cart_count': get_cart_count}

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', active_tab='profile')

@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    if 'avatar' in request.files:
        avatar = request.files['avatar']
        if avatar and allowed_file(avatar.filename):
            filename = secure_filename(f"avatar_{current_user.id}_{int(time.time())}.{avatar.filename.rsplit('.', 1)[1].lower()}")
            avatar.save(os.path.join(app.config['UPLOAD_FOLDER'], 'avatars', filename))
            
            cursor = mysql.connection.cursor()
            cursor.execute('UPDATE users SET avatar = %s WHERE id = %s', (filename, current_user.id))
            mysql.connection.commit()
            cursor.close()
    
    username = request.form.get('username')
    email = request.form.get('email')
    phone = request.form.get('phone')
    
    cursor = mysql.connection.cursor()
    cursor.execute('''
        UPDATE users 
        SET username = %s, email = %s, phone = %s 
        WHERE id = %s
    ''', (username, email, phone, current_user.id))
    mysql.connection.commit()
    cursor.close()
    
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile'))

@app.route('/orders')
@login_required
def orders():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT o.*, 
               CASE 
                   WHEN o.status = 'confirmed' THEN 'info'
                   WHEN o.status = 'processing' THEN 'primary'
                   WHEN o.status = 'shipped' THEN 'warning'
                   WHEN o.status = 'delivered' THEN 'success'
                   ELSE 'secondary'
               END as status_color
        FROM orders o 
        WHERE o.user_id = %s 
        ORDER BY o.created_at DESC
    ''', (current_user.id,))
    orders = cursor.fetchall()
    cursor.close()
    
    return render_template('profile.html', active_tab='orders', orders=orders)

@app.route('/collections')
@app.route('/collections/<category>')
def collections(category=None):
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 9  # Number of products per page
    offset = (page - 1) * per_page
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Base query
    if category:
        cursor.execute('''
            SELECT * FROM products 
            WHERE category = %s 
            ORDER BY created_at DESC 
            LIMIT %s OFFSET %s
        ''', (category, per_page, offset))
    else:
        cursor.execute('''
            SELECT * FROM products 
            ORDER BY created_at DESC 
            LIMIT %s OFFSET %s
        ''', (per_page, offset))
    
    products = cursor.fetchall()
    
    # Get total count for pagination
    if category:
        cursor.execute('SELECT COUNT(*) as count FROM products WHERE category = %s', (category,))
    else:
        cursor.execute('SELECT COUNT(*) as count FROM products')
    
    total = cursor.fetchone()['count']
    cursor.close()
    
    # Add wishlist status for each product if user is logged in
    if current_user.is_authenticated:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        for product in products:
            cursor.execute('''
                SELECT 1 FROM wishlist 
                WHERE user_id = %s AND product_id = %s
            ''', (current_user.id, product['id']))
            product['in_wishlist'] = cursor.fetchone() is not None
        cursor.close()
    
    pagination = Pagination(page=page, 
                          total=total, 
                          per_page=per_page, 
                          css_framework='bootstrap5')
    
    return render_template('collections.html',
                         products=products,
                         category=category,
                         page=page,
                         per_page=per_page,
                         pagination=pagination,
                         total_pages=(total + per_page - 1) // per_page,
                         prev_page=page-1 if page > 1 else None,
                         next_page=page+1 if page * per_page < total else None)

@app.route('/new-arrivals')
def new_arrivals():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get products created within the last 30 days
    cursor.execute('''
        SELECT p.*, 
               CASE WHEN p.is_sale = 1 THEN p.original_price ELSE NULL END as original_price
        FROM products p
        WHERE p.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        ORDER BY p.created_at DESC
        LIMIT 12
    ''')
    
    products = cursor.fetchall()
    
    # Add wishlist status if user is logged in
    if current_user.is_authenticated:
        for product in products:
            cursor.execute('''
                SELECT 1 FROM wishlist 
                WHERE user_id = %s AND product_id = %s
            ''', (current_user.id, product['id']))
            product['in_wishlist'] = cursor.fetchone() is not None
    
    cursor.close()
    return render_template('new_arrivals.html', products=products)

@app.route('/sale')
def sale():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get products on sale
    cursor.execute('''
        SELECT p.*, 
               COALESCE(AVG(r.rating), 0) as rating
        FROM products p
        LEFT JOIN reviews r ON p.id = r.product_id
        WHERE p.is_sale = TRUE
        GROUP BY p.id
        ORDER BY p.price ASC
    ''')
    
    products = cursor.fetchall()
    
    # Add wishlist status if user is logged in
    if current_user.is_authenticated:
        for product in products:
            cursor.execute('''
                SELECT 1 FROM wishlist 
                WHERE user_id = %s AND product_id = %s
            ''', (current_user.id, product['id']))
            product['in_wishlist'] = cursor.fetchone() is not None
    
    cursor.close()
    return render_template('sale.html', products=products)

@app.route('/category/<name>')
def category(name):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM products WHERE category = %s ORDER BY created_at DESC', (name,))
    products = cursor.fetchall()
    cursor.close()
    
    # Create a category object with the required attributes
    category = {
        'name': name,
        'description': 'Category description here',
        'banner_image': url_for('static', filename='images/default-banner.jpg'),
        'products': products  # Your products list/query
    }
    return render_template('category.html', category=category)

@app.route('/wishlist')
@login_required
def wishlist():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Assuming you have a wishlist table with user_id and product_id
    cursor.execute('''
        SELECT p.* FROM products p 
        JOIN wishlist w ON p.id = w.product_id 
        WHERE w.user_id = %s
    ''', (current_user.id,))
    products = cursor.fetchall()
    cursor.close()
    return render_template('wishlist.html', products=products)

@app.route('/addresses')
@login_required
def addresses():
    return render_template('profile.html', active_tab='addresses')

@app.route('/settings')
@login_required
def settings():
    return render_template('profile.html', active_tab='settings')

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    # Get product from database
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
    product = cursor.fetchone()
    cursor.close()
    
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('collections'))
    
    return render_template('product_detail.html', product=product)

@app.route('/checkout', methods=['GET'])
@login_required
def checkout():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        # Get cart items
        cursor.execute('''
            SELECT ci.*, p.name, p.price 
            FROM cart_items ci 
            JOIN products p ON ci.product_id = p.id 
            WHERE ci.user_id = %s
        ''', (current_user.id,))
        cart_items = cursor.fetchall()
        
        # Calculate totals
        subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
        shipping = 5000  # Set your shipping cost
        discount = 0     # Set discount if applicable
        total = subtotal + shipping - discount
        
        return render_template('checkout.html',
            cart_items=cart_items,
            subtotal=subtotal,
            shipping=shipping,
            discount=discount,
            total=total
        )
    finally:
        cursor.close()

@app.route('/place-order', methods=['POST'])
@login_required
def place_order():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        # Get cart items
        cursor.execute('''
            SELECT ci.*, p.price, p.stock 
            FROM cart_items ci 
            JOIN products p ON ci.product_id = p.id 
            WHERE ci.user_id = %s
        ''', (current_user.id,))
        cart_items = cursor.fetchall()
        
        if not cart_items:
            return jsonify({'success': False, 'message': 'Cart is empty'})
            
        # Calculate total
        total = sum(item['price'] * item['quantity'] for item in cart_items)
        
        # Create order
        cursor.execute('''
            INSERT INTO orders (user_id, total_amount, status) 
            VALUES (%s, %s, 'confirmed')
        ''', (current_user.id, total))
        order_id = cursor.lastrowid
        
        # Add order items
        for item in cart_items:
            cursor.execute('''
                INSERT INTO order_items (order_id, product_id, quantity, price) 
                VALUES (%s, %s, %s, %s)
            ''', (order_id, item['product_id'], item['quantity'], item['price']))
            
            # Update product stock
            cursor.execute('''
                UPDATE products 
                SET stock = stock - %s 
                WHERE id = %s
            ''', (item['quantity'], item['product_id']))
        
        # Clear cart
        cursor.execute('DELETE FROM cart_items WHERE user_id = %s', (current_user.id,))
        
        mysql.connection.commit()
        return jsonify({'success': True, 'order_id': order_id})
        
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()

# Helper function for file uploads
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.template_filter('format_currency')
def format_currency_filter(value):
    if value is None:
        return "UGX 0.00"
    return "UGX {:,.2f}".format(float(value))

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

@app.errorhandler(401)
def unauthorized(e):
    return render_template('401.html'), 401

if __name__ == '__main__':
    app.run(debug=True)
