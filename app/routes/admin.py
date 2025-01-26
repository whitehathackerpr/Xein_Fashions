from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
import MySQLdb.cursors

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get recent orders
    cursor.execute('''
        SELECT o.*, u.username 
        FROM orders o 
        JOIN users u ON o.user_id = u.id 
        ORDER BY o.created_at DESC 
        LIMIT 5
    ''')
    recent_orders = cursor.fetchall()
    
    # Get sales statistics
    cursor.execute('''
        SELECT 
            COUNT(*) as total_orders,
            SUM(total) as total_sales,
            AVG(total) as avg_order_value
        FROM orders
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    ''')
    stats = cursor.fetchone()
    
    # Get low stock products
    cursor.execute('''
        SELECT * FROM products 
        WHERE stock <= 5 
        ORDER BY stock ASC 
        LIMIT 5
    ''')
    low_stock = cursor.fetchall()
    
    cursor.close()
    
    return render_template('admin/dashboard.html', 
                         recent_orders=recent_orders,
                         stats=stats,
                         low_stock=low_stock)

@admin_bp.route('/products')
@login_required
@admin_required
def products():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM products ORDER BY created_at DESC')
    products = cursor.fetchall()
    cursor.close()
    
    return render_template('admin/products.html', products=products)

@admin_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        category = request.form['category']
        
        image = request.files['image']
        if image and allowed_file(image.filename):
            filename = secure_filename(f"product_{int(time.time())}_{image.filename}")
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = 'default-product.jpg'
        
        cursor = mysql.connection.cursor()
        cursor.execute('''
            INSERT INTO products (name, description, price, stock, category, image)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (name, description, price, stock, category, filename))
        mysql.connection.commit()
        cursor.close()
        
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin.products'))
    
    return render_template('admin/add_product.html')

@admin_bp.route('/orders')
@login_required
@admin_required
def orders():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT o.*, u.username 
        FROM orders o 
        JOIN users u ON o.user_id = u.id 
        ORDER BY o.created_at DESC
    ''')
    orders = cursor.fetchall()
    cursor.close()
    
    return render_template('admin/orders.html', orders=orders)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
    users = cursor.fetchall()
    cursor.close()
    
    return render_template('admin/users.html', users=users) 