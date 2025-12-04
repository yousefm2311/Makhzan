from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(100), nullable=True)
    role = db.Column(db.String(20), default='user')  # admin, user
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    products = db.relationship('Product', backref='category', lazy=True)
    
    def __repr__(self):
        return f'<Category {self.name}>'


class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    barcode = db.Column(db.String(50), unique=True, nullable=True)
    sku = db.Column(db.String(50), unique=True, nullable=True)
    purchase_price = db.Column(db.Float, nullable=False, default=0)
    sale_price = db.Column(db.Float, nullable=False, default=0)
    min_quantity = db.Column(db.Integer, default=0)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    inventory = db.relationship('Inventory', backref='product', uselist=False, lazy=True)
    purchase_items = db.relationship('PurchaseItem', backref='product', lazy=True)
    sale_items = db.relationship('SaleItem', backref='product', lazy=True)
    
    def __repr__(self):
        return f'<Product {self.name}>'


class Supplier(db.Model):
    __tablename__ = 'suppliers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_person = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    purchases = db.relationship('Purchase', backref='supplier', lazy=True)
    
    def __repr__(self):
        return f'<Supplier {self.name}>'


class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sales = db.relationship('Sale', backref='customer', lazy=True)
    
    def __repr__(self):
        return f'<Customer {self.name}>'


class Purchase(db.Model):
    __tablename__ = 'purchases'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    purchase_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False, default=0)
    payment_method = db.Column(db.String(20), default='cash')  # cash, card, transfer, majel
    status = db.Column(db.String(20), default='completed')  # completed, cancelled
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    amount_paid = db.Column(db.Float, nullable=False, default=0)
    due_date = db.Column(db.Date, nullable=True)
    notification_email = db.Column(db.String(120), nullable=True)
    due_reminder_sent = db.Column(db.Boolean, default=False)
    
    # Relationships
    items = db.relationship('PurchaseItem', backref='purchase', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Purchase {self.invoice_number}>'

    @property
    def due_amount(self):
        return max(0, (self.total_amount or 0) - (self.amount_paid or 0))

    @property
    def contact_email(self):
        if self.notification_email:
            return self.notification_email
        if self.supplier and self.supplier.email:
            return self.supplier.email
        return None


class PurchaseItem(db.Model):
    __tablename__ = 'purchase_items'
    
    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchases.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False, default=0)
    # لا تكتب أي علاقة مع Product هنا
    
    def __repr__(self):
        return f'<PurchaseItem {self.id}>'


class Sale(db.Model):
    __tablename__ = 'sales'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    sale_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False, default=0)
    payment_method = db.Column(db.String(20), default='cash')  # cash, card, transfer, majel
    status = db.Column(db.String(20), default='completed')  # completed, cancelled
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    amount_paid = db.Column(db.Float, nullable=False, default=0)
    due_date = db.Column(db.Date, nullable=True)
    notification_email = db.Column(db.String(120), nullable=True)
    due_reminder_sent = db.Column(db.Boolean, default=False)
    
    # Relationships
    items = db.relationship('SaleItem', backref='sale', lazy=True, cascade='all, delete-orphan')

    @property
    def profit(self):
        profit = 0
        for item in self.items:
            # item.price هو سعر البيع للوحدة
            # item.product.purchase_price هو سعر الشراء للوحدة
            if item.product and item.product.purchase_price is not None:
                profit += (item.price - item.product.purchase_price) * item.quantity
        return profit
    
    @property
    def due_amount(self):
        return max(0, (self.total_amount or 0) - (self.amount_paid or 0))

    @property
    def contact_email(self):
        if self.notification_email:
            return self.notification_email
        if self.customer and self.customer.email:
            return self.customer.email
        return None

    cashier_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    cashier = db.relationship('User', foreign_keys=[cashier_id], backref='cashier_sales', lazy=True)
    
    def __repr__(self):
        return f'<Sale {self.invoice_number}>'


class SaleItem(db.Model):
    __tablename__ = 'sale_items'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False, default=0)
    
    def __repr__(self):
        return f'<SaleItem {self.id}>'


class Inventory(db.Model):
    __tablename__ = 'inventory'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, unique=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Inventory {self.id}>'


class InventoryTransaction(db.Model):
    __tablename__ = 'inventory_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity_before = db.Column(db.Integer, nullable=False)
    quantity_change = db.Column(db.Integer, nullable=False)
    quantity_after = db.Column(db.Integer, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # purchase, sale, adjustment, return
    reference_type = db.Column(db.String(20), nullable=True)  # purchase, sale, adjustment
    reference_id = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    product = db.relationship('Product', backref='transactions', lazy=True)
    user = db.relationship('User', backref='inventory_transactions', lazy=True)
    
    def __repr__(self):
        return f'<InventoryTransaction {self.id}>'


class ReferenceProduct(db.Model):
    __tablename__ = 'reference_products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    sku = db.Column(db.String(50), nullable=True, index=True)
    barcode = db.Column(db.String(50), nullable=True, index=True)
    description = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    source_file = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ReferenceProduct {self.name}>'


class ReferenceCategory(db.Model):
    __tablename__ = 'reference_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    notes = db.Column(db.Text, nullable=True)
    source_file = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ReferenceCategory {self.name}>'


class Setting(db.Model):
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<Setting {self.key}>'
