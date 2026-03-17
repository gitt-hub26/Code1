from flask import Flask, render_template, redirect, url_for, session, request
from models import db, Product, Customer, Order, OrderItem, Payment, Delivery
from forms import LoginForm, SignupForm, DeliveryForm, PaymentForm
from werkzeug.security import generate_password_hash, check_password_hash
from decimal import Decimal
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///greenfield.db'
app.config['SECRET_KEY'] = 'change-me'
db.init_app(app)

def get_basket():
    return session.get('basket', {})

def save_basket(basket):
    session['basket'] = basket

@app.before_first_request
def create_tables():
    db.create_all()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/shop')
def shop():
    products = Product.query.all()
    return render_template('shop.html', products=products)

@app.route('/add-to-basket/<int:product_id>')
def add_to_basket(product_id):
    basket = get_basket()
    basket[str(product_id)] = basket.get(str(product_id), 0) + 1
    save_basket(basket)
    return redirect(url_for('basket'))

@app.route('/basket', methods=['GET', 'POST'])
def basket():
    basket = get_basket()
    items = []
    subtotal = Decimal('0.00')
    for pid, qty in basket.items():
        product = Product.query.get(int(pid))
        if product:
            line_total = product.price * qty
            subtotal += line_total
            items.append({'product': product, 'quantity': qty, 'line_total': line_total})
    if request.method == 'POST':
        return redirect(url_for('checkout_delivery'))
    return render_template('basket.html', items=items, subtotal=subtotal)

@app.route('/checkout/delivery', methods=['GET', 'POST'])
def checkout_delivery():
    basket = get_basket()
    if not basket:
        return redirect(url_for('shop'))
    form = DeliveryForm()
    items_total = Decimal('0.00')
    for pid, qty in basket.items():
        product = Product.query.get(int(pid))
        if product:
            items_total += product.price * qty
    delivery_cost = Decimal('3.00')
    total = items_total + delivery_cost
    if form.validate_on_submit():
        session['delivery_method'] = form.method.data
        session['order_totals'] = {
            'items_total': str(items_total),
            'delivery_cost': str(delivery_cost),
            'total': str(total)
        }
        return redirect(url_for('checkout_payment'))
    return render_template('checkout_delivery.html',
                           form=form,
                           items_total=items_total,
                           delivery_cost=delivery_cost,
                           total=total)

@app.route('/checkout/payment', methods=['GET', 'POST'])
def checkout_payment():
    basket = get_basket()
    if not basket:
        return redirect(url_for('shop'))
    totals = session.get('order_totals')
    if not totals:
        return redirect(url_for('checkout_delivery'))
    form = PaymentForm()
    if form.validate_on_submit():
        customer_id = session.get('customer_id')
        if not customer_id:
            return redirect(url_for('login'))
        order_number = str(uuid.uuid4())[:8]
        order = Order(
            order_number=order_number,
            customer_id=customer_id,
            status='Processing',
            total_amount=Decimal(totals['total'])
        )
        db.session.add(order)
        db.session.flush()
        for pid, qty in basket.items():
            product = Product.query.get(int(pid))
            if product:
                item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=qty,
                    unit_price=product.price
                )
                db.session.add(item)
        payment = Payment(
            order_id=order.id,
            amount=order.total_amount,
            method='Card',
            status='Paid'
        )
        delivery = Delivery(
            order_id=order.id,
            method=session.get('delivery_method'),
            status='Pending'
        )
        db.session.add(payment)
        db.session.add(delivery)
        db.session.commit()
        session['basket'] = {}
        return redirect(url_for('account'))
    return render_template('checkout_payment.html', form=form)

@app.route('/account')
def account():
    customer_id = session.get('customer_id')
    if not customer_id:
        return redirect(url_for('login'))
    customer = Customer.query.get(customer_id)
    orders = Order.query.filter_by(customer_id=customer_id).order_by(Order.created_at.desc()).all()
    return render_template('account.html', customer=customer, orders=orders)

@app.route('/producer/products')
def producer_products():
    if 'producer_id' not in session:
        return redirect(url_for('producer_login'))

    products = Product.query.filter_by(producer_id=session['producer_id']).all()
    return render_template('producer/products.html', products=products)

@app.route('/producer/products/add', methods=['GET', 'POST'])
def producer_add_product():
    if 'producer_id' not in session:
        return redirect(url_for('producer_login'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = Decimal(request.form['price'])
        stock = int(request.form['stock'])
        category_id = int(request.form['category'])

        product = Product(
            name=name,
            description=description,
            price=price,
            stock=stock,
            category_id=category_id,
            producer_id=session['producer_id']
        )
        db.session.add(product)
        db.session.commit()

        return redirect(url_for('producer_products'))

    categories = Category.query.all()
    return render_template('producer/add_product.html', categories=categories)

@app.route('/producer/products/edit/<int:product_id>', methods=['GET', 'POST'])
def producer_edit_product(product_id):
    if 'producer_id' not in session:
        return redirect(url_for('producer_login'))

    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        product.name = request.form['name']
        product.description = request.form['description']
        product.price = Decimal(request.form['price'])
        product.stock = int(request.form['stock'])
        product.category_id = int(request.form['category'])

        db.session.commit()
        return redirect(url_for('producer_products'))

    categories = Category.query.all()
    return render_template('producer/edit_product.html', product=product, categories=categories)

@app.route('/producer/products/delete/<int:product_id>', methods=['POST'])
def producer_delete_product(product_id):
    if 'producer_id' not in session:
        return redirect(url_for('producer_login'))

    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()

    return redirect(url_for('producer_products'))

@app.route('/producer/orders')
def producer_orders():
    if 'producer_id' not in session:
        return redirect(url_for('producer_login'))

    orders = (
        Order.query
        .join(OrderItem)
        .join(Product)
        .filter(Product.producer_id == session['producer_id'])
        .order_by(Order.created_at.desc())
        .all()
    )

    return render_template('producer/orders.html', orders=orders)

@app.route('/producer/orders/update/<int:order_id>', methods=['POST'])
def producer_update_order(order_id):
    if 'producer_id' not in session:
        return redirect(url_for('producer_login'))

    order = Order.query.get_or_404(order_id)
    new_status = request.form['status']

    order.status = new_status
    db.session.commit()

    return redirect(url_for('producer_orders'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        customer = Customer.query.filter_by(email=form.email.data).first()
        if customer and check_password_hash(customer.password_hash, form.password.data):
            session['customer_id'] = customer.id
            return redirect(url_for('account'))
    return render_template('login.html', form=form)

@app.route('/producer/login', methods=['GET', 'POST'])
def producer_login():
    form = LoginForm()
    if form.validate_on_submit():
        producer = Producer.query.filter_by(email=form.email.data).first()
        if producer and check_password_hash(producer.password_hash, form.password.data):
            session['producer_id'] = producer.id
            return redirect(url_for('producer_products'))
    return render_template('producer/login.html', form=form)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        existing = Customer.query.filter_by(email=form.email.data).first()
        if not existing:
            customer = Customer(
                full_name=form.full_name.data,
                email=form.email.data,
                password_hash=generate_password_hash(form.password.data),
                address=form.address.data
            )
            db.session.add(customer)
            db.session.commit()
            session['customer_id'] = customer.id
            return redirect(url_for('account'))
    return render_template('signup.html', form=form)

if __name__ == '__main__':
    app.run(debug=True)
