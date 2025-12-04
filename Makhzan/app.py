from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict
import os
from models import db, User, Category, Product, Supplier, Customer, Purchase, PurchaseItem, Sale, SaleItem, Inventory, InventoryTransaction, Setting, ReferenceProduct, ReferenceCategory
from forms import LoginForm, RegisterForm, CategoryForm, ProductForm, SupplierForm, CustomerForm, UserForm, SaleForm, CatalogImportForm, CategoryCatalogImportForm
from sqlalchemy.orm import joinedload
from functools import wraps
from flask import redirect, url_for, flash
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
import random
import string
import smtplib
from email.mime.text import MIMEText
from sqlalchemy import text, func

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('ليس لديك صلاحية الوصول لهذه الصفحة.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def cashier_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        if not current_user.is_authenticated or current_user.role not in ('cashier', 'admin'):
            flash('Access denied: cashier tab is required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///makhzan.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
migrate = Migrate(app, db)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables and admin user
def ensure_due_columns():
    from sqlalchemy.exc import OperationalError
    with app.app_context():
        conn = db.engine.connect()
        needs_commit = False

        def try_add(table, definition):
            nonlocal needs_commit
            try:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {definition}'))
                needs_commit = True
            except OperationalError:
                pass

        try_add('purchases', 'amount_paid FLOAT NOT NULL DEFAULT 0')
        try_add('purchases', 'due_date DATE')
        try_add('purchases', 'notification_email TEXT')
        try_add('purchases', 'due_reminder_sent BOOLEAN NOT NULL DEFAULT 0')
        try_add('sales', 'amount_paid FLOAT NOT NULL DEFAULT 0')
        try_add('sales', 'due_date DATE')
        try_add('sales', 'notification_email TEXT')
        try_add('sales', 'due_reminder_sent BOOLEAN NOT NULL DEFAULT 0')
        try_add('sales', 'cashier_id INTEGER')

        if needs_commit:
            conn.connection.commit()
        conn.close()


def ensure_reference_columns():
    from sqlalchemy.exc import OperationalError
    with app.app_context():
        conn = db.engine.connect()
        added = False

        def try_add(definition):
            nonlocal added
            try:
                conn.execute(text(f'ALTER TABLE reference_products ADD COLUMN {definition}'))
                added = True
            except OperationalError:
                pass

        try_add('notes TEXT')

        if added:
            conn.connection.commit()
        conn.close()


def create_tables():
    with app.app_context():
        db.create_all()
        ensure_due_columns()
        ensure_reference_columns()
        # Create admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@example.com',
                full_name='Admin User',
                role='admin',
                is_active=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()


class SaleProcessingError(Exception):
    """Raised when sale processing fails due to validation or inventory issues."""
    pass


def generate_invoice_number(prefix='S'):
    base = datetime.now().strftime('%y%m%d')
    while True:
        candidate = f'{prefix}{base}{random.randint(1000, 9999)}'
        if not Sale.query.filter_by(invoice_number=candidate).first():
            return candidate


def get_or_create_setting(key, default=''):
    setting = Setting.query.filter_by(key=key).first()
    if not setting:
        setting = Setting(key=key, value=default)
        db.session.add(setting)
    return setting
def create_sale_from_form(form, form_data, cashier_id):
    invoice_number = (form.invoice_number.data or '').strip()
    if invoice_number:
        if Sale.query.filter_by(invoice_number=invoice_number).first():
            raise SaleProcessingError('Invoice number already exists.')
    else:
        invoice_number = generate_invoice_number()
    form.invoice_number.data = invoice_number
    sale = Sale(
        invoice_number=invoice_number,
        customer_id=form.customer_id.data if form.customer_id.data not in (None, 0) else None,
        sale_date=form.sale_date.data,
        payment_method=form.payment_method.data,
        notes=form.notes.data,
        total_amount=0,
        amount_paid=0,
        due_date=None,
        notification_email=None,
        due_reminder_sent=False,
        cashier_id=cashier_id
    )
    db.session.add(sale)
    db.session.flush()
    total_amount = 0
    items_index = 0
    added_item = False
    while True:
        item_key = f'items-{items_index}-product_id'
        if item_key not in form_data:
                break
        product_id = form_data.get(item_key)
        try:
            product_id = int(product_id)
        except (TypeError, ValueError):
            items_index += 1
            continue
        quantity = form_data.get(f'items-{items_index}-quantity')
        price = form_data.get(f'items-{items_index}-price')
        try:
            quantity = int(quantity)
            price = float(price)
        except (TypeError, ValueError):
            items_index += 1
            continue
        if quantity <= 0 or price <= 0:
            items_index += 1
            continue
        inventory = Inventory.query.filter_by(product_id=product_id).first()
        product = Product.query.get(product_id)
        available = inventory.quantity if inventory else 0
        if not inventory or inventory.quantity < quantity:
            name = product.name if product else f'ID {product_id}'
            raise SaleProcessingError(f'Not enough stock for {name}. Available: {available}.')
        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=product_id,
            quantity=quantity,
            price=price
        )
        db.session.add(sale_item)
        inventory.quantity -= quantity
        transaction = InventoryTransaction(
            product_id=product_id,
            quantity_before=inventory.quantity + quantity,
            quantity_change=-quantity,
            quantity_after=inventory.quantity,
            transaction_type='sale',
            reference_type='sale',
            reference_id=sale.id,
            notes=f'Sale - invoice {sale.invoice_number}',
            user_id=cashier_id
        )
        db.session.add(transaction)
        total_amount += quantity * price
        added_item = True
        items_index += 1
    if not added_item or total_amount <= 0:
        raise SaleProcessingError('Add at least one product with a valid price and quantity.')
    amount_paid, due_date, notification_email = extract_due_details(total_amount, form_data)
    sale.total_amount = total_amount
    sale.amount_paid = amount_paid
    sale.due_date = due_date
    sale.notification_email = notification_email
    sale.due_reminder_sent = False
    return sale



# Routes
@app.route('/')
@login_required
def index():
    # Dashboard data
    total_products = Product.query.count()
    total_suppliers = Supplier.query.count()
    total_customers = Customer.query.count()
    
    # Recent sales
    recent_sales = Sale.query.order_by(Sale.created_at.desc()).limit(5).all()
    
    # Recent purchases
    recent_purchases = Purchase.query.order_by(Purchase.created_at.desc()).limit(5).all()
    
    # Low stock products
    low_stock_products = db.session.query(Product, Inventory).join(
        Inventory, Product.id == Inventory.product_id
    ).filter(Inventory.quantity <= Product.min_quantity).limit(5).all()
    
    # Sales data for chart
    today = datetime.now().date()
    start_date = today - timedelta(days=6)
    
    sales_data = []
    for i in range(7):
        date = start_date + timedelta(days=i)
        sales_on_date = Sale.query.filter(Sale.sale_date == date).all()
        total_sales = sum(sale.total_amount for sale in sales_on_date)
        sales_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'total': total_sales
        })
    
    due_sales = Sale.query.filter(
        Sale.payment_method == 'majel',
        Sale.status != 'cancelled',
        (Sale.total_amount - Sale.amount_paid) > 0
    ).all()
    pending_due_total = sum(sale.due_amount for sale in due_sales)
    pending_due_count = len(due_sales)
    completed_sales_total = sum(sale.total_amount for sale in Sale.query.filter(Sale.status == 'completed').all())
    net_sales_after_due = completed_sales_total - pending_due_total
    due_purchases = Purchase.query.filter(
        Purchase.payment_method == 'majel',
        Purchase.status != 'cancelled',
        Purchase.amount_paid < Purchase.total_amount
    ).all()
    pending_due_purchase_total = sum(purchase.due_amount for purchase in due_purchases)
    completed_purchases_total = sum(purchase.total_amount for purchase in Purchase.query.filter(Purchase.status == 'completed').all())
    net_purchases_after_due = completed_purchases_total - pending_due_purchase_total
    return render_template(
        'index.html',
        total_products=total_products,
        total_suppliers=total_suppliers,
        total_customers=total_customers,
        recent_sales=recent_sales,
        recent_purchases=recent_purchases,
        low_stock_products=low_stock_products,
        sales_data=sales_data,
        pending_due_total=pending_due_total,
        pending_due_count=pending_due_count,
        net_sales_after_due=net_sales_after_due,
        net_purchases_after_due=net_purchases_after_due
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')
    
    # Pass the current datetime to the template
    return render_template('login.html', form=form, now=datetime.now())

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Categories routes
@app.route('/categories')
@login_required
def categories():
    categories = Category.query.all()
    form = CategoryForm()
    return render_template('categories/index.html', categories=categories, form=form)

@app.route('/categories/add', methods=['POST'])
@login_required
@admin_required
def add_category():
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            description=form.description.data
        )
        db.session.add(category)
        db.session.commit()
        flash('تم إضافة التصنيف بنجاح', 'success')
        return redirect(url_for('categories'))
    # إذا فشل الفاليديشن، أعرض نفس صفحة التصنيفات مع الأخطاء
    categories = Category.query.all()
    flash('حدث خطأ في البيانات المدخلة. يرجى التحقق.', 'danger')
    return render_template('categories/index.html', categories=categories, form=form)

@app.route('/categories/edit/<int:id>', methods=['POST'])
@login_required
@admin_required
def edit_category(id):
    category = Category.query.get_or_404(id)
    
    # استخدام request.form بدلاً من form
    if request.method == 'POST':
        category.name = request.form.get('name')
        category.description = request.form.get('description')
        db.session.commit()
        flash('تم تحديث التصنيف بنجاح', 'success')
    
    return redirect(url_for('categories'))

@app.route('/categories/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    db.session.delete(category)
    notification_sender = Setting.query.filter_by(key='notification_sender_email').first()
    if not notification_sender:
        notification_sender = Setting(key='notification_sender_email', value='')
        db.session.add(notification_sender)

    notification_password = Setting.query.filter_by(key='notification_password').first()
    if not notification_password:
        notification_password = Setting(key='notification_password', value='')
        db.session.add(notification_password)

    notification_sender_name = Setting.query.filter_by(key='notification_sender_name').first()
    if not notification_sender_name:
        notification_sender_name = Setting(key='notification_sender_name', value='')
        db.session.add(notification_sender_name)

    db.session.commit()
    flash('تم حذف التصنيف بنجاح', 'success')
    return redirect(url_for('categories'))

# Products routes
@app.route('/products')
@login_required
def products():
    products = Product.query.all()
    return render_template('products/index.html', products=products)

@app.route('/products/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    form = ProductForm()
    
    # Get all categories for the dropdown
    categories = Category.query.all()
    
    # Check if there are any categories
    if not categories:
        # Create some default categories if none exist
        default_categories = [
            Category(name='ألبان', description='منتجات الألبان والأجبان'),
            Category(name='مشروبات', description='المشروبات الغازية والعصائر'),
            Category(name='معلبات', description='الأطعمة المعلبة'),
            Category(name='منظفات', description='منتجات التنظيف'),
            Category(name='حلويات', description='الحلويات والشوكولاتة')
        ]
        db.session.add_all(default_categories)
        db.session.commit()
        categories = Category.query.all()
    
    # Set the choices for the category dropdown
    form.category_id.choices = [(c.id, c.name) for c in categories]
    form.category_id.choices.insert(0, (0, 'بدون تصنيف'))
    
    if form.validate_on_submit():
        # image_filename = None
        # if form.image.data:
        #     image_file = form.image.data
        #     image_filename = secure_filename(image_file.filename)
        #     upload_folder = os.path.join('static', 'uploads')
        #     os.makedirs(upload_folder, exist_ok=True)
        #     image_path = os.path.join(upload_folder, image_filename)
        #     image_file.save(image_path)
        # معالجة sku
        sku = form.sku.data.strip() if form.sku.data else ''
        if not sku:
            # توليد SKU عشوائي
            while True:
                sku = 'SKU-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                if not Product.query.filter_by(sku=sku).first():
                    break
        else:
# تحقق من عدم تكرار الـ SKU
            if Product.query.filter_by(sku=sku).first():
                flash('رمز المنتج (SKU) مستخدم من قبل، يرجى اختيار رمز آخر أو تركه فارغاً ليتم توليده تلقائياً.', 'danger')
                return render_template('products/add.html', form=form)
        selected_category_id = form.category_id.data if form.category_id.data not in (None, 0) else None
        custom_category_name = (form.category_autocomplete.data or '').strip()
        if not selected_category_id and custom_category_name:
            existing_category = Category.query.filter(func.lower(Category.name) == custom_category_name.lower()).first()
            if not existing_category:
                existing_category = Category(name=custom_category_name)
                db.session.add(existing_category)
                db.session.flush()
            selected_category_id = existing_category.id
        product = Product(
            name=form.name.data,
            description=form.description.data,
            barcode=form.barcode.data,
            sku=sku,
            purchase_price=form.purchase_price.data,
            sale_price=form.sale_price.data,
            min_quantity=form.min_quantity.data,
            category_id=selected_category_id
            # image=image_filename (تم الحذف)
        )
        db.session.add(product)
        db.session.commit()
        
        # Create inventory record
        inventory = Inventory(
            product_id=product.id,
            quantity=form.initial_quantity.data
        )
        db.session.add(inventory)
        
        # Create inventory transaction
        if form.initial_quantity.data > 0:
            transaction = InventoryTransaction(
                product_id=product.id,
                quantity_before=0,
                quantity_change=form.initial_quantity.data,
                quantity_after=form.initial_quantity.data,
                transaction_type='adjustment',
                reference_type='adjustment',
                notes='الكمية الأولية عند إضافة المنتج',
                user_id=current_user.id
            )
            db.session.add(transaction)
        
        db.session.commit()
        flash('تم إضافة المنتج بنجاح', 'success')
        return redirect(url_for('products'))
    
    return render_template('products/add.html', form=form)

@app.route('/products/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    form = ProductForm(obj=product)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    form.category_id.choices.insert(0, (0, 'بدون تصنيف'))
    
    if request.method == 'GET':
        form.category_id.data = product.category_id if product.category_id else 0
        if product.inventory:
            form.initial_quantity.data = product.inventory.quantity
    
    if form.validate_on_submit():
        old_quantity = product.inventory.quantity if product.inventory else 0
        
        product.name = form.name.data
        product.description = form.description.data
        product.barcode = form.barcode.data
        product.sku = form.sku.data
        product.purchase_price = form.purchase_price.data
        product.sale_price = form.sale_price.data
        product.min_quantity = form.min_quantity.data
        product.category_id = form.category_id.data if form.category_id.data != 0 else None
        
        # Update inventory
        if not product.inventory:
            inventory = Inventory(
                product_id=product.id,
                quantity=form.initial_quantity.data
            )
            db.session.add(inventory)
        else:
            if old_quantity != form.initial_quantity.data:
                # Create inventory transaction
                transaction = InventoryTransaction(
                    product_id=product.id,
                    quantity_before=old_quantity,
                    quantity_change=form.initial_quantity.data - old_quantity,
                    quantity_after=form.initial_quantity.data,
                    transaction_type='adjustment',
                    reference_type='adjustment',
                    notes='تعديل الكمية من خلال تحرير المنتج',
                    user_id=current_user.id
                )
                db.session.add(transaction)
                
                product.inventory.quantity = form.initial_quantity.data
        
        db.session.commit()
        flash('تم تحديث المنتج بنجاح', 'success')
        return redirect(url_for('products'))
    
    return render_template('products/edit.html', form=form, product=product)

@app.route('/products/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    # احذف كل حركات المخزون المرتبطة بالمنتج
    InventoryTransaction.query.filter_by(product_id=product.id).delete()
    SaleItem.query.filter_by(product_id=product.id).delete()
    PurchaseItem.query.filter_by(product_id=product.id).delete()
    # احذف سجل المخزون المرتبط بالمنتج أولاً
    if product.inventory:
        db.session.delete(product.inventory)
    db.session.delete(product)
    db.session.commit()
    flash('تم حذف المنتج بنجاح', 'success')
    return redirect(url_for('products'))

# Suppliers routes
@app.route('/suppliers')
@login_required
def suppliers():
    suppliers = Supplier.query.all()
    return render_template('suppliers/index.html', suppliers=suppliers)

@app.route('/suppliers/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_supplier():
    form = SupplierForm()
    if form.validate_on_submit():
        supplier = Supplier(
            name=form.name.data,
            contact_person=form.contact_person.data,
            phone=form.phone.data,
            email=form.email.data,
            address=form.address.data,
            notes=form.notes.data
        )
        db.session.add(supplier)
        db.session.commit()
        flash('تم إضافة المورد بنجاح', 'success')
        return redirect(url_for('suppliers'))
    
    return render_template('suppliers/add.html', form=form)

@app.route('/suppliers/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    form = SupplierForm(obj=supplier)
    
    if form.validate_on_submit():
        supplier.name = form.name.data
        supplier.contact_person = form.contact_person.data
        supplier.phone = form.phone.data
        supplier.email = form.email.data
        supplier.address = form.address.data
        supplier.notes = form.notes.data
        db.session.commit()
        flash('تم تحديث المورد بنجاح', 'success')
        return redirect(url_for('suppliers'))
    
    return render_template('suppliers/edit.html', form=form, supplier=supplier)

@app.route('/suppliers/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    db.session.delete(supplier)
    db.session.commit()
    flash('تم حذف المورد بنجاح', 'success')
    return redirect(url_for('suppliers'))

# Customers routes
@app.route('/customers')
@login_required
def customers():
    customers = Customer.query.all()
    return render_template('customers/index.html', customers=customers)

@app.route('/customers/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_customer():
    form = CustomerForm()
    if form.validate_on_submit():
        customer = Customer(
            name=form.name.data,
            phone=form.phone.data,
            email=form.email.data,
            address=form.address.data,
            notes=form.notes.data
        )
        db.session.add(customer)
        db.session.commit()
        flash('تم إضافة العميل بنجاح', 'success')
        return redirect(url_for('customers'))
    
    return render_template('customers/add.html', form=form)

@app.route('/customers/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    form = CustomerForm(obj=customer)
    
    if form.validate_on_submit():
        customer.name = form.name.data
        customer.phone = form.phone.data
        customer.email = form.email.data
        customer.address = form.address.data
        customer.notes = form.notes.data
        db.session.commit()
        flash('تم تحديث العميل بنجاح', 'success')
        return redirect(url_for('customers'))
    
    return render_template('customers/edit.html', form=form, customer=customer)

@app.route('/customers/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    db.session.delete(customer)
    db.session.commit()
    flash('تم حذف العميل بنجاح', 'success')
    return redirect(url_for('customers'))

# Purchases routes
@app.route('/purchases')
@login_required
def purchases():
    purchases = Purchase.query.order_by(Purchase.created_at.desc()).all()
    return render_template('purchases/index.html', purchases=purchases)

@app.route('/purchases/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_purchase():
    from forms import PurchaseForm
    form = PurchaseForm()
    form.supplier_id.choices = [(s.id, s.name) for s in Supplier.query.all()]
    
    # Get all products for the dropdown
    products = Product.query.all()
    
    if request.method == 'POST':
        print('FORM DATA:', dict(request.form))
        # Process the form submission
        if form.validate_on_submit():
            # Create new purchase - remove user_id parameter
            purchase = Purchase(
                invoice_number=form.invoice_number.data,
                purchase_date=form.purchase_date.data,
                supplier_id=form.supplier_id.data,
                total_amount=0,
                payment_method=request.form.get('payment_method', 'cash'),
                notes=request.form.get('notes', ''),
                amount_paid=0,
                due_date=None,
                notification_email=None,
                due_reminder_sent=False
            )
            db.session.add(purchase)
            db.session.flush()  # Get the purchase ID
            total_amount = 0
            
            # Process purchase items
            items_count = 0
            while f'items-{items_count}-product_id' in request.form:
                product_id = request.form.get(f'items-{items_count}-product_id')
                quantity = int(request.form.get(f'items-{items_count}-quantity', 0))
                price = float(request.form.get(f'items-{items_count}-price', 0))
                
                if product_id and quantity > 0 and price > 0:
                    # Add purchase item (بدون total)
                    item = PurchaseItem(
                        purchase_id=purchase.id,
                        product_id=product_id,
                        quantity=quantity,
                        price=price
                    )
                    db.session.add(item)
                    total_amount += quantity * price
                    
                    # Update inventory
                    inventory = Inventory.query.filter_by(product_id=product_id).first()
                    if inventory:
                        old_quantity = inventory.quantity
                        inventory.quantity += quantity
                        
                        # Create inventory transaction
                        transaction = InventoryTransaction(
                            product_id=product_id,
                            quantity_before=old_quantity,
                            quantity_change=quantity,
                            quantity_after=old_quantity + quantity,
                            transaction_type='purchase',
                            reference_type='purchase',
                            reference_id=purchase.id,
                            user_id=current_user.id
                        )
                        db.session.add(transaction)
                
                items_count += 1
            
            amount_paid, due_date, notification_email = extract_due_details(total_amount, request.form)
            purchase.total_amount = total_amount
            purchase.amount_paid = amount_paid
            purchase.due_date = due_date
            purchase.notification_email = notification_email
            purchase.due_reminder_sent = False

            db.session.commit()
            flash('تم إضافة فاتورة الشراء بنجاح', 'success')
            return redirect(url_for('purchases'))
    
    return render_template('purchases/add.html', form=form, products=products)

@app.route('/purchases/view/<int:id>')
@login_required
def view_purchase(id):
    purchase = Purchase.query.options(
        joinedload(Purchase.items).joinedload(PurchaseItem.product)
    ).get_or_404(id)
    return render_template('purchases/view.html', purchase=purchase)

# Sales routes
@app.route('/sales')
@login_required
def sales():
    sales = Sale.query.order_by(Sale.created_at.desc()).all()
    total_sales = sum(sale.total_amount for sale in sales if sale.status == 'completed')
    pending_due_total = sum(
        sale.due_amount for sale in sales
        if sale.payment_method == 'majel' and sale.status != 'cancelled' and sale.due_amount > 0
    )
    pending_due_count = sum(
        1 for sale in sales
        if sale.payment_method == 'majel' and sale.status != 'cancelled' and sale.due_amount > 0
    )
    return render_template(
        'sales/index.html',
        sales=sales,
        total_sales=total_sales,
        pending_due_total=pending_due_total,
        pending_due_count=pending_due_count
    )

@app.route('/sales/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_sale():
    form = SaleForm()
    customers = Customer.query.all()
    form.customer_id.choices = [(0, '-- Select Customer --')] + [(c.id, c.name) for c in customers]
    products = Product.query.all()
    inventories = {inv.product_id: inv.quantity for inv in Inventory.query.all()}
    if not form.invoice_number.data:
        form.invoice_number.data = generate_invoice_number()
    form.sale_date.data = form.sale_date.data or datetime.now().date()
    if form.validate_on_submit():
        try:
            create_sale_from_form(form, request.form, current_user.id)
            db.session.commit()
            flash('تم إضافة فاتورة المبيعات بنجاح', 'success')
            return redirect(url_for('sales'))
        except SaleProcessingError as exc:
            db.session.rollback()
            flash(str(exc), 'danger')
    return render_template('sales/add.html', form=form, products=products, inventories=inventories)


@app.route('/sales/view/<int:id>')
@login_required
def view_sale(id):
    sale = Sale.query.options(
        joinedload(Sale.items).joinedload(SaleItem.product)
    ).get_or_404(id)
    return render_template('sales/view.html', sale=sale)

@app.route('/cashier/pos')
@login_required
@cashier_required
def cashier_pos():
    form = SaleForm()
    customers = Customer.query.all()
    form.customer_id.choices = [(0, '-- Select Customer --')] + [(c.id, c.name) for c in customers]
    products = Product.query.all()
    inventories = {inv.product_id: inv.quantity for inv in Inventory.query.all()}
    if not form.invoice_number.data:
        form.invoice_number.data = generate_invoice_number()
    form.sale_date.data = form.sale_date.data or datetime.now().date()
    form.payment_method.data = form.payment_method.data or 'cash'
    return render_template('cashier/pos.html', form=form, products=products, inventories=inventories)

@app.route('/cashier/product-info')
@login_required
@cashier_required
def cashier_product_info():
    code = (request.args.get('code') or '').strip()
    if not code:
      return jsonify({'error': 'Code missing.'}), 400
    product = None
    if code.isdigit():
        product = Product.query.filter_by(id=int(code)).first()
    if not product:
        product = Product.query.filter((Product.barcode == code) | (Product.sku == code)).first()
    if not product:
      return jsonify({'error': 'Product not found.'}), 404
    inventory = Inventory.query.filter_by(product_id=product.id).first()
    return jsonify({
        'id': product.id,
        'name': product.name,
        'price': product.sale_price,
        'available': inventory.quantity if inventory else 0,
        'barcode': product.barcode or '',
        'sku': product.sku or ''
    })

@app.route('/cashier/checkout', methods=['POST'])
@login_required
@cashier_required
def cashier_checkout():
    form = SaleForm()
    customers = Customer.query.all()
    form.customer_id.choices = [(0, '-- Select Customer --')] + [(c.id, c.name) for c in customers]
    if form.validate_on_submit():
        try:
            create_sale_from_form(form, request.form, current_user.id)
        except SaleProcessingError as exc:
            db.session.rollback()
            flash(str(exc), 'danger')
            return redirect(url_for('cashier_pos'))
        db.session.commit()
        flash('Sale recorded through cashier.', 'success')
        return redirect(url_for('cashier_pos'))
    flash('Please complete the form correctly.', 'danger')
    return redirect(url_for('cashier_pos'))

@app.route('/cashier/logs')
@login_required
@admin_required
def cashier_logs():
    cash_sales = Sale.query.options(joinedload(Sale.cashier)).filter(Sale.cashier_id.isnot(None)).order_by(Sale.created_at.desc()).all()
    return render_template('cashier/logs.html', sales=cash_sales)

@app.route('/sales/cancel/<int:id>', methods=['POST'])
@login_required
@admin_required
def cancel_sale(id):
    sale = Sale.query.get_or_404(id)
    if sale.status == 'cancelled':
        flash('تم إلغاء هذه الفاتورة بالفعل!', 'warning')
        return redirect(url_for('sales'))
    sale.status = 'cancelled'
    for item in sale.items:
        inventory = Inventory.query.filter_by(product_id=item.product_id).first()
        if inventory:
            inventory.quantity += item.quantity
            transaction = InventoryTransaction(
                product_id=item.product_id,
                quantity_before=inventory.quantity - item.quantity,
                quantity_change=item.quantity,
                quantity_after=inventory.quantity,
                transaction_type='cancel_sale',
                reference_type='sale',
                reference_id=sale.id,
                notes=f'إلغاء فاتورة بيع رقم {sale.invoice_number}',
                user_id=current_user.id
            )
            db.session.add(transaction)
    db.session.commit()
    flash('تم إلغاء الفاتورة وإعادة المنتجات للمخزون بنجاح!', 'success')
    return redirect(url_for('sales'))

# Inventory routes
@app.route('/inventory')
@login_required
def inventory():
    status = request.args.get('status', 'all')
    
    query = db.session.query(Product, Inventory).join(
        Inventory, Product.id == Inventory.product_id
    )
    
    if status == 'low':
        query = query.filter(Inventory.quantity <= Product.min_quantity, Inventory.quantity > 0)
    elif status == 'out':
        query = query.filter(Inventory.quantity <= 0)
    
    inventory_items = query.all()
    
    total_value = sum(item.quantity * item.product.purchase_price for _, item in inventory_items)
    
    return render_template('inventory/index.html', 
                          inventory=inventory_items, 
                          total_value=total_value,
                          status=status)

@app.route('/inventory/adjustment', methods=['GET', 'POST'])
@login_required
@admin_required
def inventory_adjustment():
    from forms import InventoryAdjustmentForm
    form = InventoryAdjustmentForm()
    from models import Product, Inventory, InventoryTransaction
    products = Product.query.all()
    form.product_id.choices = [(p.id, p.name) for p in products]

    if form.validate_on_submit():
        product_id = form.product_id.data
        adjustment_type = form.adjustment_type.data
        quantity = form.quantity.data
        notes = form.notes.data
        inventory = Inventory.query.filter_by(product_id=product_id).first()
        if not inventory:
            flash('لم يتم العثور على مخزون لهذا المنتج.', 'danger')
            return render_template('inventory/adjustment.html', form=form)
        old_quantity = inventory.quantity
        if adjustment_type == 'add':
            inventory.quantity += quantity
            change = quantity
        else:
            if inventory.quantity < quantity:
                flash('الكمية المدخلة أكبر من الكمية المتوفرة في المخزون.', 'danger')
                return render_template('inventory/adjustment.html', form=form)
            inventory.quantity -= quantity
            change = -quantity
        # سجل حركة المخزون
        transaction = InventoryTransaction(
            product_id=product_id,
            quantity_before=old_quantity,
            quantity_change=change,
            quantity_after=inventory.quantity,
            transaction_type='adjustment',
            reference_type='adjustment',
            notes=notes,
            user_id=current_user.id
        )
        from models import db
        db.session.add(transaction)
        db.session.commit()
        flash('تم تعديل المخزون بنجاح.', 'success')
        return redirect(url_for('inventory'))

    return render_template('inventory/adjustment.html', form=form)

@app.route('/product/transactions/<int:id>')
@login_required
def product_transactions(id):
    product = Product.query.get_or_404(id)
    transactions = InventoryTransaction.query.filter_by(product_id=id).order_by(InventoryTransaction.timestamp.desc()).all()
    return render_template('inventory/transactions.html', product=product, transactions=transactions)

# Reports routes
@app.route('/reports')
@login_required
def reports():
    categories = Category.query.order_by(Category.name).all()
    return render_template('reports/index.html', categories=categories)

@app.route('/reports/sales')
@login_required
@admin_required
def sales_report():
    start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    sales = Sale.query.filter(Sale.sale_date.between(start_date, end_date)).order_by(Sale.sale_date.desc()).all()

    total_sales = sum(sale.total_amount for sale in sales)
    total_profit = sum(sale.profit for sale in sales if sale.profit)
    average_sale = total_sales / len(sales) if sales else 0

    sales_by_date = OrderedDict()
    sales_by_payment = defaultdict(lambda: {'count': 0, 'total': 0})
    sales_by_customer = defaultdict(lambda: {'count': 0, 'total': 0})
    for sale in sales:
        date_key = sale.sale_date.strftime('%Y-%m-%d')
        day_bucket = sales_by_date.setdefault(date_key, {'count': 0, 'total': 0})
        day_bucket['count'] += 1
        day_bucket['total'] += sale.total_amount
        payment_bucket = sales_by_payment[sale.payment_method]
        payment_bucket['count'] += 1
        payment_bucket['total'] += sale.total_amount
        customer_key = sale.customer.name if sale.customer else 'غير محدد'
        customer_bucket = sales_by_customer[customer_key]
        customer_bucket['count'] += 1
        customer_bucket['total'] += sale.total_amount

    completed_sales = [sale for sale in sales if sale.status == 'completed']
    cancelled_sales = [sale for sale in sales if sale.status == 'cancelled']
    majel_sales = [sale for sale in sales if sale.payment_method == 'majel' and sale.status != 'cancelled']
    completed_total = sum(sale.total_amount for sale in completed_sales)
    cancelled_total = sum(sale.total_amount for sale in cancelled_sales)
    majel_total = sum(sale.total_amount for sale in majel_sales)
    majel_due_total = sum(sale.due_amount for sale in majel_sales)
    net_after_due = total_sales - majel_due_total
    
    report_type = request.args.get('report_type', 'summary')
    return render_template('reports/sales_report.html', 
                          sales=sales, 
                          total_sales=total_sales,
                          total_profit=total_profit,
                          average_sale=average_sale,
                          start_date=start_date,
                          end_date=end_date,
                          now=datetime.now(),
                          completed_sales=completed_sales,
                          cancelled_sales=cancelled_sales,
                          majel_sales=majel_sales,
                          completed_total=completed_total,
                          cancelled_total=cancelled_total,
                          majel_total=majel_total,
                          majel_due_total=majel_due_total,
                          net_after_due=net_after_due,
                          sales_by_date=sales_by_date,
                          sales_by_payment=sales_by_payment,
                          sales_by_customer=sales_by_customer,
                          report_type=report_type)

@app.route('/reports/purchases')
@login_required
@admin_required
def purchases_report():
    start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    purchases = Purchase.query.filter(Purchase.purchase_date.between(start_date, end_date)).order_by(Purchase.purchase_date.desc()).all()
    
    total_purchases = sum(purchase.total_amount for purchase in purchases)
    average_purchase = total_purchases / len(purchases) if purchases else 0

    purchases_by_date = OrderedDict()
    purchases_by_payment = defaultdict(lambda: {'count': 0, 'total': 0})
    purchases_by_supplier = defaultdict(lambda: {'count': 0, 'total': 0})
    for purchase in purchases:
        date_key = purchase.purchase_date.strftime('%Y-%m-%d')
        day_bucket = purchases_by_date.setdefault(date_key, {'count': 0, 'total': 0})
        day_bucket['count'] += 1
        day_bucket['total'] += purchase.total_amount
        payment_bucket = purchases_by_payment[purchase.payment_method]
        payment_bucket['count'] += 1
        payment_bucket['total'] += purchase.total_amount
        supplier_key = purchase.supplier.name if purchase.supplier else 'غير محدد'
        supplier_bucket = purchases_by_supplier[supplier_key]
        supplier_bucket['count'] += 1
        supplier_bucket['total'] += purchase.total_amount

    completed_purchases = [p for p in purchases if p.status == 'completed']
    cancelled_purchases = [p for p in purchases if p.status == 'cancelled']
    majel_purchases = [p for p in purchases if p.payment_method == 'majel' and p.status != 'cancelled']
    completed_total = sum(p.total_amount for p in completed_purchases)
    cancelled_total = sum(p.total_amount for p in cancelled_purchases)
    majel_total = sum(p.total_amount for p in majel_purchases)
    majel_due_total = sum((p.total_amount - p.amount_paid) for p in majel_purchases)
    
    report_type = request.args.get('report_type', 'summary')
    return render_template('reports/purchases_report.html', 
                          purchases=purchases, 
                          total_purchases=total_purchases,
                          average_purchase=average_purchase,
                          start_date=start_date,
                          end_date=end_date,
                          now=datetime.now(),
                          purchases_by_date=purchases_by_date,
                          purchases_by_payment=purchases_by_payment,
                          purchases_by_supplier=purchases_by_supplier,
                          completed_purchases=completed_purchases,
                          cancelled_purchases=cancelled_purchases,
                          majel_purchases=majel_purchases,
                          completed_total=completed_total,
                          cancelled_total=cancelled_total,
                          majel_total=majel_total,
                          majel_due_total=majel_due_total,
                          report_type=report_type)

@app.route('/reports/inventory')
@login_required
@admin_required
def inventory_report():
    status = request.args.get('status', 'all')
    category_id = request.args.get('category_id', type=int)
    query = db.session.query(Product, Inventory).join(
        Inventory, Product.id == Inventory.product_id
    )
    if status == 'low':
        query = query.filter(Inventory.quantity <= Product.min_quantity, Inventory.quantity > 0)
    elif status == 'out':
        query = query.filter(Inventory.quantity <= 0)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    inventory_items = query.order_by(Product.name).all()
    
    total_value = sum(item.quantity * item.product.purchase_price for _, item in inventory_items)
    categories = Category.query.order_by(Category.name).all()
    
    return render_template('reports/inventory_report.html', 
                          inventory=inventory_items, 
                          total_value=total_value,
                          now=datetime.now(),
                          status=status,
                          category_id=category_id,
                          categories=categories)

@app.route('/reports/top-selling', methods=['GET'])
def top_selling_report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    limit = request.args.get('limit', 10, type=int)

    # تحويل التواريخ
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    # جلب المنتجات الأكثر مبيعاً
    query = db.session.query(
        Product,
        db.func.sum(SaleItem.quantity).label('total_quantity')
    ).join(SaleItem, SaleItem.product_id == Product.id
    ).join(Sale, Sale.id == SaleItem.sale_id)

    if start_date:
        query = query.filter(Sale.sale_date >= start_date)
    if end_date:
        query = query.filter(Sale.sale_date <= end_date)

    query = query.group_by(Product.id).order_by(db.desc('total_quantity')).limit(limit)
    results = query.all()

    return render_template('reports/top_selling.html', results=results, start_date=start_date, end_date=end_date)

@app.route('/reports/profit', methods=['GET'])
@login_required
@admin_required
def profit_report():
    start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    group_by = request.args.get('group_by', 'day')

    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    items = db.session.query(SaleItem, Sale, Product).join(
        Sale, SaleItem.sale_id == Sale.id
    ).outerjoin(
        Product, SaleItem.product_id == Product.id
    ).filter(
        Sale.sale_date.between(start_date, end_date)
    ).all()

    total_profit = 0
    total_sales = 0
    grouped = OrderedDict()
    for sale_item, sale, product in items:
        sale_profit = 0
        if product and product.purchase_price is not None:
            sale_profit = (sale_item.price - product.purchase_price) * sale_item.quantity
        total_profit += sale_profit
        total_sales += sale_item.price * sale_item.quantity
        if group_by == 'week':
            week_label = f"{sale.sale_date.isocalendar()[0]}-{sale.sale_date.isocalendar()[1]}"
            key = f"أسبوع {week_label}"
        elif group_by == 'month':
            key = sale.sale_date.strftime('%Y-%m')
        else:
            key = sale.sale_date.strftime('%Y-%m-%d')
        bucket = grouped.setdefault(key, {'profit': 0, 'sales': 0})
        bucket['profit'] += sale_profit
        bucket['sales'] += sale_item.price * sale_item.quantity

    summary = [{
        'period': period,
        'sales': data['sales'],
        'profit': data['profit']
    } for period, data in grouped.items()]

    return render_template('reports/profit_report.html',
                          total_profit=total_profit,
                          total_sales=total_sales,
                          summary=summary,
                          start_date=start_date,
                          end_date=end_date,
                          group_by=group_by)


@app.route('/reports/customers', methods=['GET'])
@login_required
@admin_required
def customers_report():
    start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    limit = request.args.get('limit', 10, type=int)

    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    sales = Sale.query.filter(Sale.sale_date.between(start_date, end_date)).all()
    customer_stats = defaultdict(lambda: {'total_amount': 0, 'count': 0})
    for sale in sales:
        key = sale.customer.name if sale.customer else 'عميل نقدي'
        bucket = customer_stats[key]
        bucket['total_amount'] += sale.total_amount
        bucket['count'] += 1

    results = sorted(customer_stats.items(), key=lambda item: item[1]['total_amount'], reverse=True)[:limit]

    return render_template('reports/customers_report.html',
                          results=results,
                          start_date=start_date,
                          end_date=end_date,
                          limit=limit)


# Users routes
@app.route('/users')
@login_required
def users():
    # Only admin users should be able to manage users
    if current_user.role != 'admin':
        flash('ليس لديك صلاحية للوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('index'))
    
    users = User.query.all()
    return render_template('users/index.html', users=users)

@app.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if current_user.role != 'admin':
        flash('ليس لديك صلاحية للوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('index'))
    form = UserForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('البريد الإلكتروني مستخدم بالفعل من قبل مستخدم آخر.', 'danger')
            return render_template('users/add.html', form=form)
        if User.query.filter_by(username=form.username.data).first():
            flash('اسم المستخدم مستخدم بالفعل من قبل مستخدم آخر.', 'danger')
            return render_template('users/add.html', form=form)
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data,
            is_active=form.is_active.data if hasattr(form, 'is_active') else True
        )
        if not form.password.data:
            flash('يرجى تحديد كلمة مرور للمستخدم.', 'danger')
            return render_template('users/add.html', form=form)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('تم إضافة المستخدم بنجاح', 'success')
        return redirect(url_for('users'))
    return render_template('users/add.html', form=form)

@app.route('/users/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    if current_user.role != 'admin':
        flash('ليس لديك صلاحية للوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('index'))
    user = User.query.get_or_404(id)
    form = UserForm(obj=user)
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        # فقط الأدمن يمكنه تغيير الصلاحية
        if current_user.role == 'admin':
            user.role = form.role.data
        user.is_active = form.is_active.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash('تم تحديث المستخدم بنجاح', 'success')
        return redirect(url_for('users'))
    return render_template('users/edit.html', form=form, user=user)

@app.route('/users/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_user(id):
    if current_user.role != 'admin':
        flash('ليس لديك صلاحية للوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('index'))
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash('لا يمكنك حذف حسابك الحالي', 'danger')
        return redirect(url_for('users'))
    db.session.delete(user)
    db.session.commit()
    flash('تم حذف المستخدم بنجاح', 'success')
    return redirect(url_for('users'))

# Settings routes
@app.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    if current_user.role != 'admin':
        flash('Access denied for non-admin users.', 'danger')
        return redirect(url_for('index'))
    store_name = get_or_create_setting('store_name', 'Makhzan Store')
    store_address = get_or_create_setting('store_address', '')
    store_phone = get_or_create_setting('store_phone', '')
    store_email = get_or_create_setting('store_email', '')
    tax_rate = get_or_create_setting('tax_rate', '0')
    currency = get_or_create_setting('currency', 'SAR')
    notification_sender = get_or_create_setting('notification_sender_email', '')
    notification_password = get_or_create_setting('notification_password', '')
    notification_sender_name = get_or_create_setting('notification_sender_name', '')
    db.session.commit()
    if request.method == 'POST':
        store_name.value = request.form.get('store_name', '')
        store_address.value = request.form.get('store_address', '')
        store_phone.value = request.form.get('store_phone', '')
        store_email.value = request.form.get('store_email', '')
        tax_rate.value = request.form.get('tax_rate', '0')
        currency.value = request.form.get('currency', 'SAR')
        notification_sender.value = request.form.get('notification_sender_email', '')
        notification_sender_name.value = request.form.get('notification_sender_name', '')
        password = request.form.get('notification_password')
        if password:
            notification_password.value = password
        db.session.commit()
        flash('Settings saved successfully.', 'success')
        return redirect(url_for('settings'))
    return render_template('settings/index.html',
                          store_name=store_name.value,
                          store_address=store_address.value,
                          store_phone=store_phone.value,
                          store_email=store_email.value,
                          tax_rate=tax_rate.value,
                          currency=currency.value,
                          notification_sender_email=notification_sender.value,
                          notification_sender_name=notification_sender_name.value)


@app.route('/catalog/import', methods=['GET', 'POST'])
@login_required
@admin_required
def catalog_import():
    form = CatalogImportForm()
    reference_products = ReferenceProduct.query.order_by(ReferenceProduct.created_at.desc()).limit(100).all()

    if form.validate_on_submit():
        upload = form.file.data
        os.makedirs(app.instance_path, exist_ok=True)
        upload_dir = os.path.join(app.instance_path, 'reference_uploads')
        os.makedirs(upload_dir, exist_ok=True)
        filename = secure_filename(upload.filename)
        destination = os.path.join(upload_dir, filename)
        upload.save(destination)
        try:
            processed, created, updated = import_reference_catalog(destination, filename)
            flash(f'تم استيراد {processed} سجل مرجعي ({created} جديد، {updated} معدل).', 'success')
        except Exception as exc:
            flash(str(exc), 'danger')
        return redirect(url_for('catalog_import'))

    return render_template('settings/catalog_import.html', form=form, reference_products=reference_products)


@app.route('/catalog/import/load-sample', methods=['POST'])
@login_required
@admin_required
def catalog_import_sample():
    sample_path = os.path.join(app.root_path, '..', 'medical_supplies_200_notes.xlsx')
    if not os.path.exists(sample_path):
        flash('ملف المنتجات غير موجود في المستودع.', 'danger')
        return redirect(url_for('catalog_import'))
    try:
        processed, created, updated = import_reference_catalog(sample_path, os.path.basename(sample_path))
        flash(f'تم استيراد {processed} سجل من الملف النموذجي ({created} جديد، {updated} معدل).', 'success')
    except Exception as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('catalog_import'))


@app.route('/catalog/categories-import', methods=['GET', 'POST'])
@login_required
@admin_required
def category_catalog_import():
    form = CategoryCatalogImportForm()
    reference_categories = ReferenceCategory.query.order_by(ReferenceCategory.created_at.desc()).limit(100).all()

    if form.validate_on_submit():
        upload = form.file.data
        os.makedirs(app.instance_path, exist_ok=True)
        upload_dir = os.path.join(app.instance_path, 'reference_uploads')
        os.makedirs(upload_dir, exist_ok=True)
        filename = secure_filename(upload.filename)
        destination = os.path.join(upload_dir, filename)
        upload.save(destination)
        try:
            processed, created, updated = import_reference_categories(destination, filename)
            flash(f'تم استيراد {processed} تصنيف مرجعي ({created} جديد، {updated} معدل).', 'success')
        except Exception as exc:
            flash(str(exc), 'danger')
        return redirect(url_for('category_catalog_import'))

    return render_template('settings/category_import.html', form=form, reference_categories=reference_categories)


@app.route('/catalog/categories-import/load-sample', methods=['POST'])
@login_required
@admin_required
def category_catalog_import_sample():
    sample_path = os.path.join(app.root_path, '..', 'medical_categories_notes.xlsx')
    if not os.path.exists(sample_path):
        flash('ملف التصنيفات غير موجود في المستودع.', 'danger')
        return redirect(url_for('category_catalog_import'))
    try:
        processed, created, updated = import_reference_categories(sample_path, os.path.basename(sample_path))
        flash(f'تم استيراد {processed} تصنيف من الملف النموذجي ({created} جديد، {updated} معدل).', 'success')
    except Exception as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('category_catalog_import'))


@app.route('/reference/category-suggestions')
@login_required
@admin_required
def reference_category_suggestions():
    term = (request.args.get('term') or '').strip()
    if not term:
        return jsonify([])
    limit = request.args.get('limit', 10, type=int)
    suggestions = ReferenceCategory.query.filter(
        ReferenceCategory.name.ilike(f'%{term}%')
    ).order_by(ReferenceCategory.created_at.desc()).limit(limit).all()
    return jsonify([
        {'name': ref.name, 'notes': ref.notes or ''}
        for ref in suggestions
    ])


@app.route('/reference/product-info')
@login_required
@admin_required
def reference_product_info():
    code = (request.args.get('code') or '').strip()
    if not code:
      return jsonify({'error': 'يجب إدخال الكود.'}), 400
    reference = ReferenceProduct.query.filter(
        (ReferenceProduct.barcode == code) | (ReferenceProduct.sku == code)
    ).order_by(ReferenceProduct.created_at.desc()).first()
    if not reference:
        return jsonify({'error': 'المنتج غير موجود في الكتالوج المرجعي.'}), 404
    return jsonify({
        'name': reference.name,
        'sku': reference.sku or '',
        'barcode': reference.barcode or '',
        'description': reference.description or '',
        'notes': reference.notes or '',
        'source_file': reference.source_file or ''
    })
    return jsonify({
          'name': reference.name,
          'sku': reference.sku or '',
          'barcode': reference.barcode or '',
          'description': reference.description or '',
          'notes': reference.notes or '',
          'source_file': reference.source_file or ''
      })

@app.route('/settings/theme', methods=['POST'])
@login_required
@admin_required
def set_theme():
    import json
    data = request.get_json()
    theme = data.get('theme', 'light')
    from models import Setting, db
    theme_setting = Setting.query.filter_by(key='theme').first()
    if not theme_setting:
        theme_setting = Setting(key='theme', value=theme)
        db.session.add(theme_setting)
    else:
        theme_setting.value = theme
    db.session.commit()
    return '', 204

# Profile route
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = RegisterForm(obj=current_user)
    
    # Don't require password on edit
    form.password.validators = []
    form.password.flags.required = False
    form.confirm_password.validators = []
    form.confirm_password.flags.required = False
    
    # Remove role field for non-admin users
    if current_user.role != 'admin' and hasattr(form, 'role'):
        del form.role
    
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.full_name = form.full_name.data
        
        # Only admin can change role
        if current_user.role == 'admin' and hasattr(form, 'role'):
            current_user.role = form.role.data
        
        # Only update password if provided
        if form.password.data:
            current_user.set_password(form.password.data)
        
        db.session.commit()
        flash('تم تحديث الملف الشخصي بنجاح', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html', form=form)

@app.route('/print/invoice/<int:id>')
@login_required
def print_invoice(id):
    sale = Sale.query.get_or_404(id)
    from datetime import datetime
    return render_template('print/invoice.html', sale=sale, now=datetime.now())

# Due invoices and reminders
@app.route('/sales/due')
@login_required
@admin_required
def sales_due():
    due_sales = Sale.query.filter(
        Sale.payment_method == 'majel',
        Sale.status != 'cancelled',
        Sale.amount_paid < Sale.total_amount
    ).order_by(Sale.due_date.asc()).all()
    schedule_due_reminders(due_sales, 'فاتورة عميل')
    return render_template('sales/due.html', due_sales=due_sales)

@app.route('/sales/due/notify/<int:id>', methods=['POST'])
@login_required
@admin_required
def notify_due_sale(id):
    sale = Sale.query.get_or_404(id)
    if sale.payment_method != 'majel' or sale.due_amount <= 0 or sale.status == 'cancelled':
        flash('لا يمكن إرسال إشعار لفاتورة غير مستحقة أو ملغاة.', 'warning')
        return redirect(url_for('sales_due'))
    recipient = sale.contact_email
    if not recipient:
        flash('لا يوجد بريد إلكتروني لإرسال الإشعار.', 'warning')
        return redirect(url_for('sales_due'))
    days_until_due = (sale.due_date - datetime.now().date()).days if sale.due_date else None
    subject = f'تذكير بدفع فاتورة بيع {sale.invoice_number}'
    body = build_due_email_body(sale, 'فاتورة عميل', days_until_due)
    if send_due_notification_email(recipient, subject, body):
        sale.due_reminder_sent = True
        db.session.commit()
        flash('تم إرسال إشعار الدفع عبر البريد الإلكتروني.', 'success')
    else:
        flash('فشل إرسال الإشعار؛ تحقق من إعدادات البريد.', 'danger')
    return redirect(url_for('sales_due'))

@app.route('/sales/due/mark-paid/<int:id>', methods=['POST'])
@login_required
@admin_required
def mark_sale_paid(id):
    sale = Sale.query.get_or_404(id)
    sale.amount_paid = sale.total_amount
    sale.due_date = None
    sale.notification_email = None
    sale.due_reminder_sent = False
    db.session.commit()
    flash('تم تحديث الفاتورة على أنها مدفوعة.', 'success')
    return redirect(url_for('sales_due'))

@app.route('/purchases/due')
@login_required
@admin_required
def purchases_due():
    due_purchases = Purchase.query.filter(
        Purchase.payment_method == 'majel',
        Purchase.status != 'cancelled',
        Purchase.amount_paid < Purchase.total_amount
    ).order_by(Purchase.due_date.asc()).all()
    schedule_due_reminders(due_purchases, 'فاتورة مورد')
    completed_purchases_total = sum(purchase.total_amount for purchase in Purchase.query.filter(Purchase.status == 'completed').all())
    net_purchases_after_due = completed_purchases_total - sum(purchase.due_amount for purchase in due_purchases)
    return render_template('purchases/due.html', due_purchases=due_purchases)

@app.route('/purchases/due/notify/<int:id>', methods=['POST'])
@login_required
@admin_required
def notify_due_purchase(id):
    purchase = Purchase.query.get_or_404(id)
    if purchase.payment_method != 'majel' or purchase.due_amount <= 0 or purchase.status == 'cancelled':
        flash('لا يمكن إرسال إشعار لفاتورة غير مستحقة أو ملغاة.', 'warning')
        return redirect(url_for('purchases_due'))
    recipient = purchase.contact_email
    if not recipient:
        flash('لا يوجد بريد إلكتروني لإرسال الإشعار.', 'warning')
        return redirect(url_for('purchases_due'))
    days_until_due = (purchase.due_date - datetime.now().date()).days if purchase.due_date else None
    subject = f'تذكير بدفع فاتورة شراء {purchase.invoice_number}'
    body = build_due_email_body(purchase, 'فاتورة مورد', days_until_due)
    if send_due_notification_email(recipient, subject, body):
        purchase.due_reminder_sent = True
        db.session.commit()
        flash('تم إرسال إشعار السداد عبر البريد الإلكتروني.', 'success')
    else:
        flash('فشل إرسال الإشعار؛ تحقق من إعدادات البريد.', 'danger')
    return redirect(url_for('purchases_due'))

@app.route('/purchases/due/mark-paid/<int:id>', methods=['POST'])
@login_required
@admin_required
def mark_purchase_paid(id):
    purchase = Purchase.query.get_or_404(id)
    purchase.amount_paid = purchase.total_amount
    purchase.due_date = None
    purchase.notification_email = None
    purchase.due_reminder_sent = False
    db.session.commit()
    flash('تم تحديث الفاتورة على أنها مدفوعة.', 'success')
    return redirect(url_for('purchases_due'))

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def parse_due_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None

def extract_due_details(total_amount, form_data):
    payment_method = form_data.get('payment_method', 'cash')
    amount_paid = safe_float(form_data.get('amount_paid'))
    due_date = parse_due_date(form_data.get('due_date'))
    notification_email = (form_data.get('notification_email') or '').strip()
    if payment_method != 'majel':
        return total_amount, None, None
    amount_paid = max(0.0, min(total_amount, amount_paid))
    return amount_paid, due_date, notification_email or None


def import_reference_catalog(filepath, source_label=None):
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError('مطلوب تثبيت مكتبة openpyxl لقراءة ملفات Excel.') from exc

    # ملف مش موجود
    if not os.path.exists(filepath):
        raise ValueError('مسار ملف Excel غير موجود.')

    workbook = load_workbook(filepath, read_only=True, data_only=True)
    sheet = workbook.active
    rows = sheet.iter_rows(values_only=True)

    header_row = next(rows, None)
    if not header_row:
        raise ValueError('ملف Excel لا يحتوي على صف عناوين (Header).')

    # تجهيز العناوين
    normalized_headers = [str(col).strip().lower() if col else '' for col in header_row]

    def find_index(keywords):
        for idx, header in enumerate(normalized_headers):
            if any(keyword in header for keyword in keywords):
                return idx
        return None

    # البحث عن الأعمدة
    name_idx = find_index(['اسم المنتج', 'product'])
    sku_idx = find_index(['sku'])
    barcode_idx = find_index(['barcode', 'code', 'باركود'])
    desc_idx = find_index(['desc', 'description', 'وصف'])
    notes_idx = find_index(['notes', 'ملاحظات', 'remarks', 'comments'])

    # لو مفيش عمود اسم المنتج
    if name_idx is None:
        raise ValueError('لم يتم العثور على عمود اسم المنتج داخل ملف Excel.')

    processed = created = updated = 0
    source_label = source_label or os.path.basename(filepath)

    for row in rows:
        if not row:
            continue

        name_cell = row[name_idx] if name_idx < len(row) else None
        if not name_cell:
            continue

        name = str(name_cell).strip()
        if not name:
            continue

        sku = ''
        barcode = ''
        description = ''
        notes = ''

        if sku_idx is not None and sku_idx < len(row) and row[sku_idx]:
            sku = str(row[sku_idx]).strip()

        if barcode_idx is not None and barcode_idx < len(row) and row[barcode_idx]:
            barcode = str(row[barcode_idx]).strip()

        if desc_idx is not None and desc_idx < len(row) and row[desc_idx]:
            description = str(row[desc_idx]).strip()

        if notes_idx is not None and notes_idx < len(row) and row[notes_idx]:
            notes = str(row[notes_idx]).strip()

        processed += 1

        reference = None

        # البحث لو موجود قبل كده
        if barcode:
            reference = ReferenceProduct.query.filter_by(barcode=barcode).first()

        if not reference and sku:
            reference = ReferenceProduct.query.filter_by(sku=sku).first()

        if not reference:
            normalized_name = name.lower()
            reference = ReferenceProduct.query.filter(func.lower(ReferenceProduct.name) == normalized_name).first()

        # إنشاء جديد
        if not reference:
            reference = ReferenceProduct(
                name=name,
                sku=sku or None,
                barcode=barcode or None,
                description=description or None,
                notes=notes or None,
                source_file=source_label
            )
            db.session.add(reference)
            created += 1

        # تحديث القديم
        else:
            reference.name = name
            reference.sku = sku or reference.sku
            reference.barcode = barcode or reference.barcode
            reference.description = description or reference.description
            reference.notes = notes or reference.notes
            reference.source_file = source_label
            updated += 1

    if processed:
        db.session.commit()

    return processed, created, updated

def import_reference_categories(filepath, source_label=None):
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError('openpyxl is required to read Excel files.') from exc

    if not os.path.exists(filepath):
        raise ValueError('ملف تصنيفات المراجع غير موجود.')

    workbook = load_workbook(filepath, read_only=True, data_only=True)
    sheet = workbook.active
    rows = sheet.iter_rows(values_only=True)
    header_row = next(rows, None)
    if not header_row:
        raise ValueError('ملف Excel لا يحتوي على صف رؤوس.')

    normalized_headers = [str(col).strip().lower() if col else '' for col in header_row]

    def find_index(keywords):
        for idx, header in enumerate(normalized_headers):
            if any(keyword in header for keyword in keywords):
                return idx
        return None

    name_idx = find_index(['تصنيف', 'classification', 'category', 'name'])
    notes_idx = find_index(['notes', 'ملاحظات', 'remarks', 'comments'])

    if name_idx is None:
        raise ValueError('الملف لا يحتوي على عمود اسم التصنيف.')

    processed = created = updated = 0
    source_label = source_label or os.path.basename(filepath)

    for row in rows:
        if not row:
            continue
        name_cell = row[name_idx] if name_idx < len(row) else None
        if not name_cell:
            continue
        name = str(name_cell).strip()
        if not name:
            continue
        notes = ''
        if notes_idx is not None and notes_idx < len(row) and row[notes_idx]:
            notes = str(row[notes_idx]).strip()

        processed += 1
        normalized_name = name.lower()
        reference = ReferenceCategory.query.filter(func.lower(ReferenceCategory.name) == normalized_name).first()

        if not reference:
            reference = ReferenceCategory(
                name=name,
                notes=notes or None,
                source_file=source_label
            )
            db.session.add(reference)
            created += 1
        else:
            reference.name = name
            reference.notes = notes or reference.notes
            reference.source_file = source_label
            updated += 1

    if processed:
        db.session.commit()

    return processed, created, updated


def get_notification_config():
    keys = ['notification_sender_email', 'notification_password', 'notification_sender_name']
    settings = Setting.query.filter(Setting.key.in_(keys)).all()
    return {s.key: s.value for s in settings}


def send_due_notification_email(recipient, subject, body):
    config = get_notification_config()
    sender = config.get('notification_sender_email')
    password = config.get('notification_password')
    sender_name = config.get('notification_sender_name') or sender
    if not sender or not password or not recipient:
        return False
    msg = MIMEText(body, 'html')
    msg['Subject'] = subject
    msg['From'] = f"{sender_name} <{sender}>"
    msg['To'] = recipient
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender, password)
            smtp.send_message(msg)
        return True
    except Exception as exc:
        app.logger.error('Failed to send reminder email: %s', exc)
        return False


def build_due_email_body(record, entity_label, days_until_due=None):
    due_date = record.due_date.strftime('%Y-%m-%d') if record.due_date else 'غير محدد'
    header = f'<p>تذكير بالفاتورة {entity_label} <strong>{record.invoice_number}</strong>.</p>'
    totals = f'<p>الإجمالي: {record.total_amount:.2f} &nbsp; مدفوع: {record.amount_paid:.2f} &nbsp; المتبقي: {record.due_amount:.2f}.</p>'
    date_line = f'<p>تاريخ الاستحقاق: {due_date}.</p>'
    reminder_line = f'<p>باقي {days_until_due} يوم.</p>' if days_until_due is not None else ''
    preamble = '<p>يرجى مراجعة التذكير قبل تاريخ الاستحقاق.</p>'
    closing = '<p>برجاء تسوية الرصيد المتبقي.</p>'
    return f"{preamble}{header}{totals}{date_line}{reminder_line}{closing}"


def schedule_due_reminders(records, entity_label):
    today = datetime.now().date()
    updated = False
    for record in records:
        if record.status == 'cancelled' or record.payment_method != 'majel':
            continue
        if not record.due_date or record.due_amount <= 0:
            continue
        if record.due_reminder_sent:
            continue
        days_until_due = (record.due_date - today).days
        if days_until_due < 0 or days_until_due > 2:
            continue
        recipient = record.contact_email
        if not recipient:
            continue
        subject = f'تذكير استحقاق {entity_label} {record.invoice_number}'
        body = build_due_email_body(record, entity_label, days_until_due)
        if send_due_notification_email(recipient, subject, body):
            record.due_reminder_sent = True
            updated = True
    if updated:
        db.session.commit()


# Add more routes for purchases, sales, inventory, etc.

@app.context_processor
def inject_settings():
    from models import Setting
    settings = {s.key: s.value for s in Setting.query.all()}
    return dict(settings=settings)

if __name__ == '__main__':
    create_tables()  # Call the function to create tables and admin user
    app.run(debug=True)
