from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager
from models import User, Product, Category, Supplier, Customer, Purchase, PurchaseItem, Sale, SaleItem, Inventory, InventoryMovement, UserActivity
from forms import LoginForm, RegisterForm, ProductForm, CategoryForm, SupplierForm, CustomerForm, PurchaseForm, SaleForm
from datetime import datetime
from sqlalchemy.sql import func

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def register_routes(app):
    # مسارات المصادقة
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.remember.data)
                
                # تسجيل نشاط تسجيل الدخول
                activity = UserActivity(
                    user_id=user.id,
                    activity_type='login',
                    description=f'تسجيل دخول المستخدم {user.username}'
                )
                db.session.add(activity)
                db.session.commit()
                
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash('فشل تسجيل الدخول. يرجى التحقق من اسم المستخدم وكلمة المرور', 'danger')
        
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        # تسجيل نشاط تسجيل الخروج
        activity = UserActivity(
            user_id=current_user.id,
            activity_type='logout',
            description=f'تسجيل خروج المستخدم {current_user.username}'
        )
        db.session.add(activity)
        db.session.commit()
        
        logout_user()
        return redirect(url_for('login'))

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated and current_user.role != 'admin':
            return redirect(url_for('dashboard'))
        
        form = RegisterForm()
        if form.validate_on_submit():
            hashed_password = generate_password_hash(form.password.data)
            user = User(
                username=form.username.data,
                email=form.email.data,
                password=hashed_password,
                role=form.role.data
            )
            db.session.add(user)
            db.session.commit()
            
            flash('تم إنشاء الحساب بنجاح!', 'success')
            return redirect(url_for('login'))
        
        return render_template('register.html', form=form)

    # لوحة التحكم
    @app.route('/dashboard')
    @login_required
    def dashboard():
        # إحصائيات سريعة
        products_count = Product.query.count()
        low_stock_count = Inventory.query.filter(Inventory.quantity <= Inventory.min_quantity).count()
        sales_today = Sale.query.filter(Sale.sale_date >= datetime.today().date()).count()
        purchases_pending = Purchase.query.filter_by(status='pending').count()
        
        # آخر المبيعات
        recent_sales = Sale.query.order_by(Sale.sale_date.desc()).limit(5).all()
        
        # آخر المشتريات
        recent_purchases = Purchase.query.order_by(Purchase.purchase_date.desc()).limit(5).all()
        
        # المنتجات منخفضة المخزون
        low_stock_products = db.session.query(Product, Inventory).join(Inventory).filter(
            Inventory.quantity <= Inventory.min_quantity
        ).limit(5).all()
        
        return render_template('dashboard.html', 
                              products_count=products_count,
                              low_stock_count=low_stock_count,
                              sales_today=sales_today,
                              purchases_pending=purchases_pending,
                              recent_sales=recent_sales,
                              recent_purchases=recent_purchases,
                              low_stock_products=low_stock_products)

    # مسارات المنتجات
    @app.route('/products')
    @login_required
    def products():
        products = db.session.query(Product, Inventory).outerjoin(Inventory).all()
        return render_template('products/index.html', products=products)

    @app.route('/products/add', methods=['GET', 'POST'])
    @login_required
    def add_product():
        form = ProductForm()
        form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
        
        if form.validate_on_submit():
            product = Product(
                name=form.name.data,
                description=form.description.data,
                sku=form.sku.data,
                category_id=form.category_id.data,
                purchase_price=form.purchase_price.data,
                selling_price=form.selling_price.data
            )
            db.session.add(product)
            db.session.commit()
            
            # إنشاء سجل المخزون
            inventory = Inventory(
                product_id=product.id,
                quantity=form.initial_quantity.data,
                min_quantity=form.min_quantity.data
            )
            db.session.add(inventory)
            
            # تسجيل حركة المخزون الأولية
            if form.initial_quantity.data > 0:
                movement = InventoryMovement(
                    inventory_id=inventory.id,
                    movement_type='in',
                    quantity=form.initial_quantity.data,
                    reference='initial',
                    notes='الكمية الأولية'
                )
                db.session.add(movement)
            
            # تسجيل نشاط المستخدم
            activity = UserActivity(
                user_id=current_user.id,
                activity_type='create',
                description=f'إضافة منتج جديد: {product.name}'
            )
            db.session.add(activity)
            
            db.session.commit()
            flash('تمت إضافة المنتج بنجاح!', 'success')
            return redirect(url_for('products'))
        
        return render_template('products/add.html', form=form)

    @app.route('/products/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_product(id):
        product = Product.query.get_or_404(id)
        inventory = Inventory.query.filter_by(product_id=id).first()
        
        form = ProductForm(obj=product)
        form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
        
        if form.validate_on_submit():
            product.name = form.name.data
            product.description = form.description.data
            product.sku = form.sku.data
            product.category_id = form.category_id.data
            product.purchase_price = form.purchase_price.data
            product.selling_price = form.selling_price.data
            
            if inventory:
                old_quantity = inventory.quantity
                inventory.min_quantity = form.min_quantity.data
                
                # إذا تغيرت الكمية، نسجل حركة مخزون
                if old_quantity != form.initial_quantity.data:
                    quantity_diff = form.initial_quantity.data - old_quantity
                    movement_type = 'in' if quantity_diff > 0 else 'out'
                    
                    movement = InventoryMovement(
                        inventory_id=inventory.id,
                        movement_type=movement_type,
                        quantity=abs(quantity_diff),
                        reference='adjustment',
                        notes='تعديل الكمية'
                    )
                    db.session.add(movement)
                    inventory.quantity = form.initial_quantity.data
            else:
                # إنشاء سجل مخزون جديد إذا لم يكن موجودًا
                inventory = Inventory(
                    product_id=product.id,
                    quantity=form.initial_quantity.data,
                    min_quantity=form.min_quantity.data
                )
                db.session.add(inventory)
                
                if form.initial_quantity.data > 0:
                    movement = InventoryMovement(
                        inventory_id=inventory.id,
                        movement_type='in',
                        quantity=form.initial_quantity.data,
                        reference='initial',
                        notes='الكمية الأولية'
                    )
                    db.session.add(movement)
            
            # تسجيل نشاط المستخدم
            activity = UserActivity(
                user_id=current_user.id,
                activity_type='update',
                description=f'تعديل منتج: {product.name}'
            )
            db.session.add(activity)
            
            db.session.commit()
            flash('تم تحديث المنتج بنجاح!', 'success')
            return redirect(url_for('products'))
        
        # ملء النموذج بالبيانات الحالية
        if inventory:
            form.initial_quantity.data = inventory.quantity
            form.min_quantity.data = inventory.min_quantity
        
        return render_template('products/edit.html', form=form, product=product)

    @app.route('/products/delete/<int:id>', methods=['POST'])
    @login_required
    def delete_product(id):
        product = Product.query.get_or_404(id)
        inventory = Inventory.query.filter_by(product_id=id).first()
        
        # حذف حركات المخزون أولاً
        if inventory:
            InventoryMovement.query.filter_by(inventory_id=inventory.id).delete()
            db.session.delete(inventory)
        
        # تسجيل نشاط المستخدم
        activity = UserActivity(
            user_id=current_user.id,
            activity_type='delete',
            description=f'حذف منتج: {product.name}'
        )
        db.session.add(activity)
        
        db.session.delete(product)
        db.session.commit()
        
        flash('تم حذف المنتج بنجاح!', 'success')
        return redirect(url_for('products'))

    # مسارات الفئات
    @app.route('/categories')
    @login_required
    def categories():
        categories = Category.query.all()
        return render_template('categories/index.html', categories=categories)

    @app.route('/categories/add', methods=['GET', 'POST'])
    @login_required
    def add_category():
        form = CategoryForm()
        
        if form.validate_on_submit():
            category = Category(
                name=form.name.data,
                description=form.description.data
            )
            db.session.add(category)
            
            # تسجيل نشاط المستخدم
            activity = UserActivity(
                user_id=current_user.id,
                activity_type='create',
                description=f'إضافة فئة جديدة: {category.name}'
            )
            db.session.add(activity)
            
            db.session.commit()
            flash('تمت إضافة الفئة بنجاح!', 'success')
            return redirect(url_for('categories'))
        
        return render_template('categories/add.html', form=form)

    # مسارات الموردين
    @app.route('/suppliers')
    @login_required
    def suppliers():
        suppliers = Supplier.query.all()
        return render_template('suppliers/index.html', suppliers=suppliers)

    @app.route('/suppliers/add', methods=['GET', 'POST'])
    @login_required
    def add_supplier():
        form = SupplierForm()
        
        if form.validate_on_submit():
            supplier = Supplier(
                name=form.name.data,
                contact_person=form.contact_person.data,
                email=form.email.data,
                phone=form.phone.data,
                address=form.address.data
            )
            db.session.add(supplier)
            
            # تسجيل نشاط المستخدم
            activity = UserActivity(
                user_id=current_user.id,
                activity_type='create',
                description=f'إضافة مورد جديد: {supplier.name}'
            )
            db.session.add(activity)
            
            db.session.commit()
            flash('تمت إضافة المورد بنجاح!', 'success')
            return redirect(url_for('suppliers'))
        
        return render_template('suppliers/add.html', form=form)

    # مسارات العملاء
    @app.route('/customers')
    @login_required
    def customers():
        customers = Customer.query.all()
        return render_template('customers/index.html', customers=customers)

    @app.route('/customers/add', methods=['GET', 'POST'])
    @login_required
    def add_customer():
        form = CustomerForm()
        
        if form.validate_on_submit():
            customer = Customer(
                name=form.name.data,
                email=form.email.data,
                phone=form.phone.data,
                address=form.address.data
            )
            db.session.add(customer)
            
            # تسجيل نشاط المستخدم
            activity = UserActivity(
                user_id=current_user.id,
                activity_type='create',
                description=f'إضافة عميل جديد: {customer.name}'
            )
            db.session.add(activity)
            
            db.session.commit()
            flash('تمت إضافة العميل بنجاح!', 'success')
            return redirect(url_for('customers'))
        
        return render_template('customers/add.html', form=form)

    # مسارات المشتريات
    @app.route('/purchases')
    @login_required
    def purchases():
        purchases = Purchase.query.order_by(Purchase.purchase_date.desc()).all()
        return render_template('purchases/index.html', purchases=purchases)

    @app.route('/purchases/add', methods=['GET', 'POST'])
    @login_required
    def add_purchase():
        form = PurchaseForm()
        form.supplier_id.choices = [(s.id, s.name) for s in Supplier.query.all()]
        
        if request.method == 'POST':
            supplier_id = request.form.get('supplier_id')
            invoice_number = request.form.get('invoice_number')
            purchase_date = datetime.strptime(request.form.get('purchase_date'), '%Y-%m-%d')
            notes = request.form.get('notes')
            
            # إنشاء طلب شراء جديد
            purchase = Purchase(
                supplier_id=supplier_id,
                invoice_number=invoice_number,
                purchase_date=purchase_date,
                notes=notes,
                created_by=current_user.id,
                status='pending'
            )
            db.session.add(purchase)
            db.session.flush()  # للحصول على معرف الطلب
            
            # معالجة عناصر الطلب
            product_ids = request.form.getlist('product_id[]')
            quantities = request.form.getlist('quantity[]')
            unit_prices = request.form.getlist('unit_price[]')
            
            total_amount = 0
            
            for i in range(len(product_ids)):
                product_id = int(product_ids[i])
                quantity = int(quantities[i])
                unit_price = float(unit_prices[i])
                total_price = quantity * unit_price
                
                # إضافة عنصر الطلب
                purchase_item = PurchaseItem(
                    purchase_id=purchase.id,
                    product_id=product_id,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=total_price
                )
                db.session.add(purchase_item)
                
                total_amount += total_price
            
            purchase.total_amount = total_amount
            
            # تسجيل نشاط المستخدم
            activity = UserActivity(
                user_id=current_user.id,
                activity_type='create',
                description=f'إنشاء طلب شراء جديد رقم: {purchase.invoice_number}'
            )
            db.session.add(activity)
            
            db.session.commit()
            flash('تم إنشاء طلب الشراء بنجاح!', 'success')
            return redirect(url_for('purchases'))
        
        products = Product.query.all()
        return render_template('purchases/add.html', form=form, products=products)

    @app.route('/purchases/receive/<int:id>', methods=['POST'])
    @login_required
    def receive_purchase(id):
        purchase = Purchase.query.get_or_404(id)
        
        if purchase.status == 'received':
            flash('تم استلام هذا الطلب بالفعل!', 'warning')
            return redirect(url_for('purchases'))
        
        purchase.status = 'received'
        
        # تحديث المخزون
        for item in purchase.items:
            inventory = Inventory.query.filter_by(product_id=item.product_id).first()
            
            if inventory:
                # تسجيل حركة المخزون
                movement = InventoryMovement(
                    inventory_id=inventory.id,
                    movement_type='in',
                    quantity=item.quantity,
                    reference=f'PO-{purchase.id}',
                    notes=f'استلام طلب شراء رقم {purchase.invoice_number}'
                )
                db.session.add(movement)
                
                # تحديث كمية المخزون
                inventory.quantity += item.quantity
                inventory.last_stock_update = datetime.utcnow()
            else:
                # إنشاء سجل مخزون جديد إذا لم يكن موجودًا
                inventory = Inventory(
                    product_id=item.product_id,
                    quantity=item.quantity
                )
                db.session.add(inventory)
                db.session.flush()
                
                movement = InventoryMovement(
                    inventory_id=inventory.id,
                    movement_type='in',
                    quantity=item.quantity,
                    reference=f'PO-{purchase.id}',
                    notes=f'استلام طلب شراء رقم {purchase.invoice_number}'
                )
                db.session.add(movement)
        
        # تسجيل نشاط المستخدم
        activity = UserActivity(
            user_id=current_user.id,
            activity_type='update',
            description=f'استلام طلب شراء رقم: {purchase.invoice_number}'
        )
        db.session.add(activity)
        
        db.session.commit()
        flash('تم استلام الطلب وتحديث المخزون بنجاح!', 'success')
        return redirect(url_for('purchases'))

    # مسارات المبيعات
    @app.route('/sales')
    @login_required
    def sales():
        sales = Sale.query.order_by(Sale.sale_date.desc()).all()
        return render_template('sales/index.html', sales=sales)

    @app.route('/sales/add', methods=['GET', 'POST'])
    @login_required
    def add_sale():
        form = SaleForm()
        form.customer_id.choices = [(c.id, c.name) for c in Customer.query.all()]
        
        if request.method == 'POST':
            customer_id = request.form.get('customer_id')
            invoice_number = request.form.get('invoice_number')
            sale_date = datetime.strptime(request.form.get('sale_date'), '%Y-%m-%d')
            notes = request.form.get('notes')
            
            # إنشاء فاتورة بيع جديدة
            sale = Sale(
                customer_id=customer_id,
                invoice_number=invoice_number,
                sale_date=sale_date,
                notes=notes,
                created_by=current_user.id,
                status='completed'
            )
            db.session.add(sale)
            db.session.flush()  # للصول على معرف الفاتورة
            
            # معالجة عناصر الفاتورة
            product_ids = request.form.getlist('product_id[]')
            quantities = request.form.getlist('quantity[]')
            unit_prices = request.form.getlist('unit_price[]')
            
            total_amount = 0
            inventory_error = False
            
            for i in range(len(product_ids)):
                product_id = int(product_ids[i])
                quantity = int(quantities[i])
                unit_price = float(unit_prices[i])
                total_price = quantity * unit_price
                
                # التحقق من توفر المخزون
                inventory = Inventory.query.filter_by(product_id=product_id).first()
                if not inventory or inventory.quantity < quantity:
                    inventory_error = True
                    flash(f'المنتج غير متوفر بالكمية المطلوبة: {Product.query.get(product_id).name}', 'danger')
                    continue
                
                # إضافة عنصر الفاتورة
                sale_item = SaleItem(
                    sale_id=sale.id,
                    product_id=product_id,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=total_price
                )
                db.session.add(sale_item)
                
                # تحديث المخزون
                inventory.quantity -= quantity
                inventory.last_stock_update = datetime.utcnow()
                
                # تسجيل حركة المخزون
                movement = InventoryMovement(
                    inventory_id=inventory.id,
                    movement_type='out',
                    quantity=quantity,
                    reference=f'INV-{sale.id}',
                    notes=f'بيع - فاتورة رقم {sale.invoice_number}'
                )
                db.session.add(movement)
                
                total_amount += total_price
            
            if inventory_error:
                db.session.rollback()
                return redirect(url_for('add_sale'))
            
            sale.total_amount = total_amount
            
            # تسجيل نشاط المستخدم
            activity = UserActivity(
                user_id=current_user.id,
                activity_type='create',
                description=f'إنشاء فاتورة بيع جديدة رقم: {sale.invoice_number}'
            )
            db.session.add(activity)
            
            db.session.commit()
            flash('تم إنشاء فاتورة البيع بنجاح!', 'success')
            return redirect(url_for('sales'))
        
        products = db.session.query(Product, Inventory).join(Inventory).filter(Inventory.quantity > 0).all()
        return render_template('sales/add.html', form=form, products=products)

    @app.route('/sales/view/<int:id>')
    @login_required
    def view_sale(id):
        sale = Sale.query.get_or_404(id)
        return render_template('sales/view.html', sale=sale)

    @app.route('/sales/cancel/<int:id>', methods=['POST'])
    @login_required
    def cancel_sale(id):
        sale = Sale.query.get_or_404(id)
        
        if sale.status == 'cancelled':
            flash('تم إلغاء هذه الفاتورة بالفعل!', 'warning')
            return redirect(url_for('sales'))
        
        sale.status = 'cancelled'
        
        # إعادة المنتجات للمخزون
        for item in sale.items:
            inventory = Inventory.query.filter_by(product_id=item.product_id).first()
            
            if inventory:
                # تسجيل حركة المخزون
                movement = InventoryMovement(
                    inventory_id=inventory.id,
                    movement_type='in',
                    quantity=item.quantity,
                    reference=f'INV-CANCEL-{sale.id}',
                    notes=f'إلغاء فاتورة بيع رقم {sale.invoice_number}'
                )
                db.session.add(movement)
                
                # تحديث كمية المخزون
                inventory.quantity += item.quantity
                inventory.last_stock_update = datetime.utcnow()
        
        # تسجيل نشاط المستخدم
        activity = UserActivity(
            user_id=current_user.id,
            activity_type='update',
            description=f'إلغاء فاتورة بيع رقم: {sale.invoice_number}'
        )
        db.session.add(activity)
        
        db.session.commit()
        flash('تم إلغاء الفاتورة وإعادة المنتجات للمخزون بنجاح!', 'success')
        return redirect(url_for('sales'))

    # مسارات المخزون والجرد
    @app.route('/inventory')
    @login_required
    def inventory():
        inventory_items = db.session.query(Product, Inventory).join(Inventory).all()
        return render_template('inventory/index.html', inventory_items=inventory_items)

    @app.route('/inventory/movements')
    @login_required
    def inventory_movements():
        movements = db.session.query(
            InventoryMovement, Inventory, Product
        ).join(
            Inventory, InventoryMovement.inventory_id == Inventory.id
        ).join(
            Product, Inventory.product_id == Product.id
        ).order_by(
            InventoryMovement.timestamp.desc()
        ).all()
        
        return render_template('inventory/movements.html', movements=movements)

    @app.route('/inventory/adjust/<int:product_id>', methods=['GET', 'POST'])
    @login_required
    def adjust_inventory(product_id):
        product = Product.query.get_or_404(product_id)
        inventory = Inventory.query.filter_by(product_id=product_id).first()
        
        if request.method == 'POST':
            new_quantity = int(request.form.get('new_quantity'))
            notes = request.form.get('notes')
            
            if inventory:
                old_quantity = inventory.quantity
                quantity_diff = new_quantity - old_quantity
                
                if quantity_diff != 0:
                    movement_type = 'in' if quantity_diff > 0 else 'out'
                    
                    # تسجيل حركة المخزون
                    movement = InventoryMovement(
                        inventory_id=inventory.id,
                        movement_type=movement_type,
                        quantity=abs(quantity_diff),
                        reference='adjustment',
                        notes=notes or 'تعديل يدوي للمخزون'
                    )
                    db.session.add(movement)
                    
                    # تحديث كمية المخزون
                    inventory.quantity = new_quantity
                    inventory.last_stock_update = datetime.utcnow()
                    
                    # تسجيل نشاط المستخدم
                    activity = UserActivity(
                        user_id=current_user.id,
                        activity_type='update',
                        description=f'تعديل مخزون المنتج: {product.name} من {old_quantity} إلى {new_quantity}'
                    )
                    db.session.add(activity)
                    
                    db.session.commit()
                    flash('تم تعديل المخزون بنجاح!', 'success')
                else:
                    flash('لم يتم إجراء أي تغيير على المخزون.', 'info')
            else:
                flash('لم يتم العثور على سجل المخزون للمنتج المحدد.', 'danger')
            
            return redirect(url_for('inventory'))
        
        return render_template('inventory/adjust.html', product=product, inventory=inventory)

    # مسارات التقارير
    @app.route('/reports')
    @login_required
    def reports():
        return render_template('reports/index.html')

    @app.route('/reports/sales')
    @login_required
    def sales_report():
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = Sale.query
        
        if start_date:
            query = query.filter(Sale.sale_date >= datetime.strptime(start_date, '%Y-%m-%d'))
        
        if end_date:
            query = query.filter(Sale.sale_date <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
        
        sales = query.order_by(Sale.sale_date.desc()).all()
        
        total_amount = sum(sale.total_amount for sale in sales if sale.status == 'completed')
        
        return render_template('reports/sales.html', 
                              sales=sales, 
                              total_amount=total_amount,
                              start_date=start_date,
                              end_date=end_date)

    @app.route('/reports/purchases')
    @login_required
    def purchases_report():
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = Purchase.query
        
        if start_date:
            query = query.filter(Purchase.purchase_date >= datetime.strptime(start_date, '%Y-%m-%d'))
        
        if end_date:
            query = query.filter(Purchase.purchase_date <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
        
        purchases = query.order_by(Purchase.purchase_date.desc()).all()
        
        total_amount = sum(purchase.total_amount for purchase in purchases if purchase.status == 'received')
        
        return render_template('reports/purchases.html', 
                              purchases=purchases, 
                              total_amount=total_amount,
                              start_date=start_date,
                              end_date=end_date)

    @app.route('/reports/inventory')
    @login_required
    def inventory_report():
        inventory_items = db.session.query(
            Product, 
            Inventory,
            Category
        ).join(
            Inventory
        ).join(
            Category, 
            Product.category_id == Category.id
        ).all()
        
        return render_template('reports/inventory.html', inventory_items=inventory_items)

    @app.route('/reports/profit')
    @login_required
    def profit_report():
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # استعلام المبيعات
        sales_query = db.session.query(
            SaleItem.product_id,
            func.sum(SaleItem.quantity).label('sold_quantity'),
            func.sum(SaleItem.total_price).label('sales_amount')
        ).join(
            Sale, SaleItem.sale_id == Sale.id
        ).filter(
            Sale.status == 'completed'
        )
        
        if start_date:
            sales_query = sales_query.filter(Sale.sale_date >= datetime.strptime(start_date, '%Y-%m-%d'))
        
        if end_date:
            sales_query = sales_query.filter(Sale.sale_date <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
        
        sales_data = sales_query.group_by(SaleItem.product_id).all()
        
        # استعلام تكلفة المنتجات المباعة
        product_costs = {}
        total_sales = 0
        total_cost = 0
        total_profit = 0
        
        profit_data = []
        
        for product_id, sold_quantity, sales_amount in sales_data:
            product = Product.query.get(product_id)
            cost_amount = sold_quantity * product.purchase_price
            profit = sales_amount - cost_amount
            
            profit_data.append({
                'product': product,
                'sold_quantity': sold_quantity,
                'sales_amount': sales_amount,
                'cost_amount': cost_amount,
                'profit': profit,
                'profit_margin': (profit / sales_amount) * 100 if sales_amount > 0 else 0
            })
            
            total_sales += sales_amount
            total_cost += cost_amount
            total_profit += profit
        
        return render_template('reports/profit.html', 
                              profit_data=profit_data,
                              total_sales=total_sales,
                              total_cost=total_cost,
                              total_profit=total_profit,
                              start_date=start_date,
                              end_date=end_date)

    # مسارات المستخدمين والأنشطة
    @app.route('/users')
    @login_required
    def users():
        if current_user.role != 'admin':
            flash('ليس لديك صلاحية للوصول إلى هذه الصفحة.', 'danger')
            return redirect(url_for('dashboard'))
        
        users = User.query.all()
        return render_template('users/index.html', users=users)

    @app.route('/activities')
    @login_required
    def activities():
        if current_user.role != 'admin':
            flash('ليس لديك صلاحية للوصول إلى هذه الصفحة.', 'danger')
            return redirect(url_for('dashboard'))
        
        activities = db.session.query(
            UserActivity, User
        ).join(
            User, UserActivity.user_id == User.id
        ).order_by(
            UserActivity.timestamp.desc()
        ).limit(100).all()
        
        return render_template('activities/index.html', activities=activities)

    # واجهات برمجة التطبيقات API
    @app.route('/api/products')
    @login_required
    def api_products():
        products = db.session.query(
            Product.id,
            Product.name,
            Product.sku,
            Product.selling_price,
            Inventory.quantity
        ).join(
            Inventory
        ).filter(
            Inventory.quantity > 0
        ).all()
        
        products_list = [{
            'id': p.id,
            'name': p.name,
            'sku': p.sku,
            'price': p.selling_price,
            'quantity': p.quantity
        } for p in products]
        
        return jsonify(products_list)

    @app.route('/api/product/<int:id>')
    @login_required
    def api_product(id):
        product = Product.query.get_or_404(id)
        inventory = Inventory.query.filter_by(product_id=id).first()
        
        product_data = {
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'description': product.description,
            'purchase_price': product.purchase_price,
            'selling_price': product.selling_price,
            'quantity': inventory.quantity if inventory else 0
        }
        
        return jsonify(product_data)

    @app.route('/api/low-stock')
    @login_required
    def api_low_stock():
        low_stock = db.session.query(
            Product.id,
            Product.name,
            Inventory.quantity,
            Inventory.min_quantity
        ).join(
            Inventory
        ).filter(
            Inventory.quantity <= Inventory.min_quantity
        ).all()
        
        low_stock_list = [{
            'id': p.id,
            'name': p.name,
            'quantity': p.quantity,
            'min_quantity': p.min_quantity
        } for p in low_stock]
        
        return jsonify(low_stock_list)

    # صفحة الطباعة
    @app.route('/print/invoice/<int:id>')
    @login_required
    def print_invoice(id):
        sale = Sale.query.get_or_404(id)
        return render_template('print/invoice.html', sale=sale)

    @app.route('/print/purchase/<int:id>')
    @login_required
    def print_purchase(id):
        purchase = Purchase.query.get_or_404(id)
        return render_template('print/purchase.html', purchase=purchase)