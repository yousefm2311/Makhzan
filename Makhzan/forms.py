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
        ('user', 'مستخدم'),
        ('cashier', 'بائع')
    ], validators=[DataRequired()])
    is_active = BooleanField('نشط')
    password = PasswordField('كلمة المرور', validators=[Optional(), Length(min=4), Regexp(r'^[a-zA-Z0-9]+$', message='كلمة المرور يجب أن تتكون من حروف أو أرقام فقط')])
    confirm_password = PasswordField('تأكيد كلمة المرور', validators=[Optional(), EqualTo('password')])

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
