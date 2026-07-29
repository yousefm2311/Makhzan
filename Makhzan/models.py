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
    role = db.Column(db.String(30), default='user')
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=True)
    custom_permissions = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    branch = db.relationship('Branch', foreign_keys=[branch_id], lazy=True)
    
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


class Branch(db.Model):
    __tablename__ = 'branches'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    location = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employees = db.relationship('Employee', backref='branch', lazy=True)
    storage_locations = db.relationship('StorageLocation', backref='branch', lazy=True)

    def __repr__(self):
        return f'<Branch {self.code}>'


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


class StorageLocation(db.Model):
    __tablename__ = 'storage_locations'

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    location_type = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    stocks = db.relationship('ProductLocationStock', backref='location', lazy=True)

    def __repr__(self):
        return f'<StorageLocation {self.code}>'


class ProductLocationStock(db.Model):
    __tablename__ = 'product_location_stocks'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('storage_locations.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = db.relationship('Product', backref='location_stocks', lazy=True)

    __table_args__ = (
        db.UniqueConstraint('product_id', 'location_id', name='uq_product_location_stock'),
    )

    def __repr__(self):
        return f'<ProductLocationStock {self.product_id}:{self.location_id}>'


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


class Employee(db.Model):
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    employee_code = db.Column(db.String(50), unique=True, nullable=True, index=True)
    name = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(120), nullable=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=True)
    job_title = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    issues = db.relationship('StockIssue', backref='employee', lazy=True)

    def __repr__(self):
        return f'<Employee {self.name}>'


class StockIssue(db.Model):
    __tablename__ = 'stock_issues'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    issue_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    purpose = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product', backref='stock_issues', lazy=True)
    user = db.relationship('User', backref='stock_issues', lazy=True)

    def __repr__(self):
        return f'<StockIssue {self.id}>'


class DamageRecord(db.Model):
    __tablename__ = 'damage_records'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    damage_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    reason = db.Column(db.String(200), nullable=True)
    responsibility = db.Column(db.String(120), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product', backref='damage_records', lazy=True)
    user = db.relationship('User', backref='damage_records', lazy=True)

    def __repr__(self):
        return f'<DamageRecord {self.id}>'


class StockIssueRequest(db.Model):
    __tablename__ = 'stock_issue_requests'

    id = db.Column(db.Integer, primary_key=True)
    request_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    purpose = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending', index=True)
    requested_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    executed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    rejected_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime, nullable=True)
    executed_at = db.Column(db.DateTime, nullable=True)
    rejected_at = db.Column(db.DateTime, nullable=True)
    approved_signature = db.Column(db.String(200), nullable=True)
    executed_signature = db.Column(db.String(200), nullable=True)
    rejected_signature = db.Column(db.String(200), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    stock_issue_id = db.Column(db.Integer, db.ForeignKey('stock_issues.id'), nullable=True)

    product = db.relationship('Product', backref='issue_requests', lazy=True)
    employee = db.relationship('Employee', backref='issue_requests', lazy=True)
    requested_by = db.relationship('User', foreign_keys=[requested_by_id], lazy=True)
    approved_by = db.relationship('User', foreign_keys=[approved_by_id], lazy=True)
    executed_by = db.relationship('User', foreign_keys=[executed_by_id], lazy=True)
    rejected_by = db.relationship('User', foreign_keys=[rejected_by_id], lazy=True)
    stock_issue = db.relationship('StockIssue', lazy=True)

    def __repr__(self):
        return f'<StockIssueRequest {self.request_number}>'


class EmployeeReturn(db.Model):
    __tablename__ = 'employee_returns'

    id = db.Column(db.Integer, primary_key=True)
    return_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    return_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    condition = db.Column(db.String(50), default='usable')
    notes = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    signed_signature = db.Column(db.String(200), nullable=True)

    product = db.relationship('Product', backref='employee_returns', lazy=True)
    employee = db.relationship('Employee', backref='returns', lazy=True)
    user = db.relationship('User', backref='employee_returns', lazy=True)

    def __repr__(self):
        return f'<EmployeeReturn {self.return_number}>'


class Stocktake(db.Model):
    __tablename__ = 'stocktakes'

    id = db.Column(db.Integer, primary_key=True)
    count_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=True)
    count_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), default='draft', index=True)
    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    rejected_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejected_at = db.Column(db.DateTime, nullable=True)
    approved_signature = db.Column(db.String(200), nullable=True)
    rejected_signature = db.Column(db.String(200), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    branch = db.relationship('Branch', backref='stocktakes', lazy=True)
    created_by = db.relationship('User', foreign_keys=[created_by_id], lazy=True)
    approved_by = db.relationship('User', foreign_keys=[approved_by_id], lazy=True)
    rejected_by = db.relationship('User', foreign_keys=[rejected_by_id], lazy=True)
    items = db.relationship('StocktakeItem', backref='stocktake', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Stocktake {self.count_number}>'


class StocktakeItem(db.Model):
    __tablename__ = 'stocktake_items'

    id = db.Column(db.Integer, primary_key=True)
    stocktake_id = db.Column(db.Integer, db.ForeignKey('stocktakes.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    system_quantity = db.Column(db.Integer, nullable=False, default=0)
    counted_quantity = db.Column(db.Integer, nullable=False, default=0)
    variance = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)

    product = db.relationship('Product', lazy=True)

    def __repr__(self):
        return f'<StocktakeItem {self.id}>'


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(80), nullable=False, index=True)
    entity_type = db.Column(db.String(80), nullable=True, index=True)
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', backref='audit_logs', lazy=True)

    def __repr__(self):
        return f'<AuditLog {self.action}>'


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
