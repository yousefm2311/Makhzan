from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, FloatField, IntegerField, SelectField, DateField
from wtforms.validators import DataRequired, Email, EqualTo, Optional, Length, NumberRange, Regexp
from datetime import datetime
from flask_wtf.file import FileField, FileAllowed, FileRequired

class LoginForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired()])
    password = PasswordField('كلمة المرور', validators=[DataRequired()])
    remember_me = BooleanField('تذكرني')

class RegisterForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    full_name = StringField('الاسم الكامل', validators=[DataRequired()])
    password = PasswordField('كلمة المرور', validators=[DataRequired(), Length(min=4), Regexp(r'^[a-zA-Z0-9]+$', message='كلمة المرور يجب أن تتكون من حروف أو أرقام فقط')])
    confirm_password = PasswordField('تأكيد كلمة المرور', validators=[DataRequired(), EqualTo('password')])

class CategoryForm(FlaskForm):
    name = StringField('اسم التصنيف', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('الوصف', validators=[Optional()])

class ProductForm(FlaskForm):
    name = StringField('اسم المنتج', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('الوصف', validators=[Optional()])
    barcode = StringField('الباركود', validators=[Optional(), Length(max=50)])
    sku = StringField('رمز المنتج (SKU)', validators=[Optional(), Length(max=50)])
    purchase_price = FloatField('سعر الشراء', validators=[DataRequired(), NumberRange(min=0)])
    sale_price = FloatField('سعر البيع', validators=[DataRequired(), NumberRange(min=0)])
    min_quantity = IntegerField('الحد الأدنى للكمية', validators=[DataRequired(), NumberRange(min=0)])
    initial_quantity = IntegerField('الكمية الأولية', validators=[DataRequired(), NumberRange(min=0)])
    category_id = SelectField('التصنيف', coerce=int, validators=[DataRequired()])
    category_autocomplete = StringField('تصنيف مرجعي', validators=[Optional(), Length(max=100)])

class SupplierForm(FlaskForm):
    name = StringField('اسم المورد', validators=[DataRequired(), Length(max=100)])
    contact_person = StringField('الشخص المسؤول', validators=[Optional(), Length(max=100)])
    phone = StringField('رقم الهاتف', validators=[Optional(), Length(max=20)])
    email = StringField('البريد الإلكتروني', validators=[Optional(), Email()])
    address = TextAreaField('العنوان', validators=[Optional()])
    notes = TextAreaField('ملاحظات', validators=[Optional()])

class CustomerForm(FlaskForm):
    name = StringField('اسم العميل', validators=[DataRequired(), Length(max=100)])
    phone = StringField('رقم الهاتف', validators=[Optional(), Length(max=20)])
    email = StringField('البريد الإلكتروني', validators=[Optional(), Email()])
    address = TextAreaField('العنوان', validators=[Optional()])
    notes = TextAreaField('ملاحظات', validators=[Optional()])

class PurchaseForm(FlaskForm):
    invoice_number = StringField('رقم الفاتورة', validators=[DataRequired()])
    purchase_date = DateField('تاريخ الشراء', validators=[DataRequired()], default=datetime.now().date)
    supplier_id = SelectField('المورد', coerce=int, validators=[DataRequired()])
    notes = TextAreaField('ملاحظات', validators=[Optional()])
    payment_method = SelectField('طريقة الدفع', choices=[
        ('cash', 'نقدي'),
        ('card', 'بطاقة ائتمان'),
        ('transfer', 'تحويل بنكي'),
        ('majel', 'ماجلة'),
    ], validators=[DataRequired()])
    notes = TextAreaField('ملاحظات', validators=[Optional()])

class SaleForm(FlaskForm):
    invoice_number = StringField('رقم الفاتورة', validators=[DataRequired(), Length(max=50)])
    customer_id = SelectField('العميل', coerce=int, validators=[Optional()])
    sale_date = DateField('تاريخ البيع', validators=[DataRequired()])
    payment_method = SelectField('طريقة الدفع', choices=[
        ('cash', 'نقدي'),
        ('card', 'بطاقة ائتمان'),
        ('transfer', 'تحويل بنكي'),
        ('majel', 'ماجلة'),
    ], validators=[DataRequired()])
    notes = TextAreaField('ملاحظات', validators=[Optional()])

class InventoryAdjustmentForm(FlaskForm):
    product_id = SelectField('المنتج', coerce=int, validators=[DataRequired()])
    adjustment_type = SelectField('نوع التعديل', choices=[
        ('add', 'إضافة'),
        ('subtract', 'خصم')
    ], validators=[DataRequired()])
    quantity = IntegerField('الكمية', validators=[DataRequired(), NumberRange(min=1)])
    notes = TextAreaField('ملاحظات', validators=[Optional()])

class ReportForm(FlaskForm):
    start_date = DateField('من تاريخ', validators=[DataRequired()])
    end_date = DateField('إلى تاريخ', validators=[DataRequired()])
    report_type = SelectField('نوع التقرير', choices=[
        ('summary', 'ملخص'),
        ('detailed', 'تفصيلي')
    ], validators=[DataRequired()])

class UserForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    role = SelectField('الصلاحية', choices=[
        ('admin', 'ادمن'),
        ('warehouse_manager', 'مدير مخزن'),
        ('approver', 'مدير اعتماد'),
        ('auditor', 'مراجع'),
        ('requester', 'طالب عهدة'),
        ('user', 'مستخدم')
    ], validators=[DataRequired()])
    is_active = BooleanField('نشط')
    password = PasswordField('كلمة المرور', validators=[Optional(), Length(min=4), Regexp(r'^[a-zA-Z0-9]+$', message='كلمة المرور يجب أن تتكون من حروف أو أرقام فقط')])
    confirm_password = PasswordField('تأكيد كلمة المرور', validators=[Optional(), EqualTo('password')])


class BranchForm(FlaskForm):
    name = StringField('اسم الفرع', validators=[DataRequired(), Length(max=120)])
    code = StringField('كود الفرع', validators=[DataRequired(), Length(max=50)])
    location = StringField('مكان الفرع', validators=[Optional(), Length(max=200)])
    notes = TextAreaField('ملاحظات', validators=[Optional()])
    is_active = BooleanField('نشط', default=True)


class StorageLocationForm(FlaskForm):
    branch_id = SelectField('الفرع', coerce=int, validators=[Optional()])
    name = StringField('اسم موقع التخزين', validators=[DataRequired(), Length(max=120)])
    code = StringField('كود الموقع', validators=[DataRequired(), Length(max=50)])
    location_type = StringField('نوع الموقع', validators=[Optional(), Length(max=50)])
    notes = TextAreaField('ملاحظات', validators=[Optional()])
    is_active = BooleanField('نشط', default=True)


class EmployeeForm(FlaskForm):
    employee_code = StringField('كود الموظف', validators=[DataRequired(), Length(max=50)])
    name = StringField('اسم الموظف', validators=[DataRequired(), Length(max=120)])
    branch_id = SelectField('الفرع', coerce=int, validators=[Optional()])
    department = StringField('الإدارة / القسم', validators=[Optional(), Length(max=120)])
    job_title = StringField('المسمى الوظيفي', validators=[Optional(), Length(max=120)])
    phone = StringField('رقم الهاتف', validators=[Optional(), Length(max=30)])
    email = StringField('البريد الإلكتروني', validators=[Optional(), Email()])
    is_active = BooleanField('نشط', default=True)
    notes = TextAreaField('ملاحظات', validators=[Optional()])


class StockIssueForm(FlaskForm):
    product_id = SelectField('الصنف', coerce=int, validators=[DataRequired()])
    employee_id = SelectField('الموظف المستلم', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('الكمية المنصرفة', validators=[DataRequired(), NumberRange(min=1)])
    issue_date = DateField('تاريخ الصرف', validators=[DataRequired()], default=datetime.now().date)
    purpose = StringField('الغرض / جهة الاستخدام', validators=[Optional(), Length(max=200)])
    notes = TextAreaField('ملاحظات', validators=[Optional()])


class DamageRecordForm(FlaskForm):
    product_id = SelectField('الصنف', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('كمية الهالك', validators=[DataRequired(), NumberRange(min=1)])
    damage_date = DateField('تاريخ الهالك', validators=[DataRequired()], default=datetime.now().date)
    reason = StringField('سبب الهالك', validators=[Optional(), Length(max=200)])
    responsibility = StringField('المسؤولية / المكان', validators=[Optional(), Length(max=120)])
    notes = TextAreaField('ملاحظات', validators=[Optional()])


class StockIssueRequestForm(FlaskForm):
    product_id = SelectField('الصنف', coerce=int, validators=[DataRequired()])
    employee_id = SelectField('الموظف المستلم', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('الكمية المطلوبة', validators=[DataRequired(), NumberRange(min=1)])
    purpose = StringField('الغرض / جهة الاستخدام', validators=[Optional(), Length(max=200)])
    notes = TextAreaField('ملاحظات', validators=[Optional()])


class EmployeeReturnForm(FlaskForm):
    product_id = SelectField('الصنف', coerce=int, validators=[DataRequired()])
    employee_id = SelectField('الموظف', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('الكمية المرتجعة', validators=[DataRequired(), NumberRange(min=1)])
    return_date = DateField('تاريخ المرتجع', validators=[DataRequired()], default=datetime.now().date)
    condition = SelectField('الحالة', choices=[
        ('usable', 'صالح للاستخدام'),
        ('damaged', 'تالف'),
        ('needs_review', 'يحتاج مراجعة')
    ], validators=[DataRequired()])
    notes = TextAreaField('ملاحظات', validators=[Optional()])


class StocktakeForm(FlaskForm):
    branch_id = SelectField('الفرع', coerce=int, validators=[Optional()])
    count_date = DateField('تاريخ الجرد', validators=[DataRequired()], default=datetime.now().date)
    notes = TextAreaField('ملاحظات', validators=[Optional()])


class StocktakeItemForm(FlaskForm):
    product_id = SelectField('الصنف', coerce=int, validators=[DataRequired()])
    counted_quantity = IntegerField('الكمية الفعلية', validators=[DataRequired(), NumberRange(min=0)])
    notes = TextAreaField('ملاحظات', validators=[Optional()])


class SettingsForm(FlaskForm):
    company_name = StringField('اسم الشركة', validators=[DataRequired()])
    company_address = TextAreaField('عنوان الشركة', validators=[Optional()])
    company_phone = StringField('رقم الهاتف', validators=[Optional()])
    company_email = StringField('البريد الإلكتروني', validators=[Optional(), Email()])
    tax_rate = FloatField('نسبة الضريبة (%)', validators=[Optional(), NumberRange(min=0, max=100)])
    currency_symbol = StringField('رمز العملة', validators=[Optional()])
    low_stock_threshold = IntegerField('حد التنبيه للمخزون المنخفض', validators=[Optional(), NumberRange(min=0)])


class CatalogImportForm(FlaskForm):
    file = FileField('ملف Excel', validators=[
        FileRequired(message='يرجى اختيار ملف Excel.'),
        FileAllowed(['xls', 'xlsx'], 'الملفات المقبولة: xls أو xlsx.')
    ])


class CategoryCatalogImportForm(FlaskForm):
    file = FileField('ملف تصنيفات Excel', validators=[
        FileRequired(message='يرجى اختيار ملف Excel للتصنيفات.'),
        FileAllowed(['xls', 'xlsx'], 'الملفات المقبولة: xls أو xlsx.')
    ])
