import os
import io
import qrcode
import base64
import random
import string
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Category, Product, Order, OrderItem, CartItem, EscrowDispute
from config import Config
from translations import TRANSLATIONS, SUPPORTED_LANGUAGES, CURRENCIES, CRYPTO_RATES, SEO_KEYWORDS

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def generate_order_number():
    chars = string.ascii_uppercase + string.digits
    return 'SH-' + ''.join(random.choices(chars, k=6))

def generate_qr_code(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def get_cart_items():
    cart = session.get('cart', {})
    items = []
    total = 0
    for product_id, quantity in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            subtotal = product.price * quantity
            total += subtotal
            items.append({'product': product, 'quantity': quantity, 'subtotal': subtotal})
    return items, total

def get_cart_count():
    cart = session.get('cart', {})
    return sum(cart.values())

app.jinja_env.globals['get_cart_count'] = get_cart_count


# ---- i18n / currency helpers ----

def get_lang():
    return session.get('lang', 'en')

def get_currency():
    return session.get('currency', 'USD')

def t(key):
    """Translate a key using the current session language."""
    lang = get_lang()
    lang_map = TRANSLATIONS.get(lang, TRANSLATIONS['en'])
    return lang_map.get(key, TRANSLATIONS['en'].get(key, key))

def format_price(amount_usd):
    """Convert a USD price to the session currency and return a formatted string."""
    currency = get_currency()
    info = CURRENCIES.get(currency, CURRENCIES['USD'])
    converted = amount_usd * info['rate']
    return f"{info['symbol']}{converted:,.2f}"

def crypto_equivalent(amount_usd, coin):
    """Return how much of `coin` equals `amount_usd`."""
    rate = CRYPTO_RATES.get(coin, 1.0)
    amount_coin = amount_usd * rate
    if coin == 'BTC':
        return f"{amount_coin:.8f} BTC"
    elif coin == 'XMR':
        return f"{amount_coin:.6f} XMR"
    elif coin == 'USDT':
        return f"{amount_coin:.2f} USDT"
    elif coin == 'TRX':
        return f"{amount_coin:.2f} TRX"
    return f"{amount_coin} {coin}"

@app.context_processor
def inject_globals():
    currency = get_currency()
    lang = get_lang()
    return dict(
        t=t,
        format_price=format_price,
        crypto_equivalent=crypto_equivalent,
        current_lang=lang,
        current_currency=currency,
        supported_languages=SUPPORTED_LANGUAGES,
        supported_currencies=CURRENCIES,
        crypto_rates=CRYPTO_RATES,
        seo_keywords=SEO_KEYWORDS,
        contact_email=app.config['CONTACT_EMAIL'],
    )


# ---- Language & Currency switch routes ----

@app.route('/set-language/<lang>')
def set_language(lang):
    if lang in SUPPORTED_LANGUAGES:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

@app.route('/set-currency/<currency>')
def set_currency(currency):
    if currency in CURRENCIES:
        session['currency'] = currency
    return redirect(request.referrer or url_for('index'))


def create_sample_data():
    if User.query.filter_by(username='admin').first():
        return
    admin = User(username='admin', email='admin@shadowhub.com', is_admin=True)
    admin.set_password('admin123')
    db.session.add(admin)

    # ── Top-level categories ──
    top_level = [
        {'name': 'Clone Cards',        'slug': 'clone-cards',        'description': 'Cloned credit and debit cards'},
        {'name': 'Counterfeit',        'slug': 'counterfeit',        'description': 'Counterfeit bills and currency'},
        {'name': 'Documents',          'slug': 'documents',          'description': 'Fake and real documents'},
        {'name': 'Drugs for sale',     'slug': 'drugs-for-sale',     'description': 'All types of drugs available'},
        {'name': 'Guns for sale',      'slug': 'guns-for-sale',      'description': 'Firearms and weapons'},
        {'name': 'Hire Expert Hacker', 'slug': 'hire-expert-hacker', 'description': 'Professional hacking services'},
        {'name': 'Hit Man',            'slug': 'hit-man',            'description': 'Hitman services'},
        {'name': 'Other Drugs',        'slug': 'other-drugs',        'description': 'Miscellaneous drugs'},
    ]
    cat_map = {}
    for data in top_level:
        cat = Category(**data)
        db.session.add(cat)
        cat_map[data['slug']] = cat
    db.session.flush()

    # ── Subcategories for Drugs for sale ──
    drugs_subs = [
        ('Anabolic steroids',       'anabolic-steroids'),
        ('Anxiety pills',           'anxiety-pills'),
        ('Cannabinoids',            'cannabinoids'),
        ('Cannabis',                'cannabis'),
        ('Cocaine',                 'cocaine'),
        ('Nembutal pentobarbital',  'nembutal-pentobarbital'),
        ('Opioids',                 'opioids'),
        ('Pain Killer',             'pain-killer'),
        ('Poisons',                 'poisons'),
    ]
    for name, slug in drugs_subs:
        sub = Category(name=name, slug=slug,
                       description=f'{name} products',
                       parent_id=cat_map['drugs-for-sale'].id)
        db.session.add(sub)
        cat_map[slug] = sub

    # ── Subcategories for Guns for sale ──
    guns_subs = [
        ('Ammunitions', 'ammunitions'),
        ('Hand guns',   'hand-guns'),
        ('Rifles',      'rifles'),
    ]
    for name, slug in guns_subs:
        sub = Category(name=name, slug=slug,
                       description=f'{name} for sale',
                       parent_id=cat_map['guns-for-sale'].id)
        db.session.add(sub)
        cat_map[slug] = sub
    db.session.flush()

    # ── Sample products spread across categories ──
    products_data = [
        {'name': 'Clone Visa Card',        'slug': 'clone-visa-card',        'description': 'Cloned Visa card with high balance, ready to use.', 'price': 299.99, 'stock': 88,  'cat': 'clone-cards',        'is_featured': True},
        {'name': 'US Dollar Bills Bundle', 'slug': 'us-dollar-bills-bundle', 'description': 'High-quality counterfeit USD bills, undetectable.', 'price': 199.99, 'stock': 99,  'cat': 'counterfeit',        'is_featured': True},
        {'name': 'Fake Passport',          'slug': 'fake-passport',          'description': 'Authentic-looking fake passport, any country.', 'price': 899.99, 'stock': 25,  'cat': 'documents',          'is_featured': True},
        {'name': 'Anabolic Steroid Kit',   'slug': 'anabolic-steroid-kit',   'description': 'Complete anabolic steroid cycle kit.', 'price': 149.99, 'stock': 66,  'cat': 'anabolic-steroids',  'is_featured': True},
        {'name': 'OG Kush (7g)',           'slug': 'og-kush-7g',             'description': 'Premium OG Kush cannabis, discreet packaging.', 'price': 79.99,  'stock': 77,  'cat': 'cannabis',           'is_featured': True},
        {'name': 'Pure Cocaine (1g)',      'slug': 'pure-cocaine-1g',        'description': '99% pure cocaine, lab tested.', 'price': 129.99, 'stock': 77,  'cat': 'cocaine',            'is_featured': True},
        {'name': 'Glock 19 Gen 5',        'slug': 'glock-19-gen-5',         'description': 'Glock 19 Gen 5 handgun, brand new, untraceable.', 'price': 599.99, 'stock': 21,  'cat': 'hand-guns',          'is_featured': True},
        {'name': 'Hacking Service',        'slug': 'hacking-service',        'description': 'Professional ethical and grey-hat hacking services.', 'price': 499.99, 'stock': 1,   'cat': 'hire-expert-hacker', 'is_featured': True},
    ]
    for p in products_data:
        cat_slug = p.pop('cat')
        prod = Product(
            name=p['name'], slug=p['slug'], description=p['description'],
            price=p['price'], stock=p['stock'], is_featured=p['is_featured'],
            is_active=True,
            category_id=cat_map[cat_slug].id,
            image_url=f"https://via.placeholder.com/400x300/1a1a2e/6c63ff?text={p['name'].replace(' ', '+')}"
        )
        db.session.add(prod)
    db.session.commit()


# ---- Routes ----

@app.route('/')
def index():
    featured = Product.query.filter_by(is_featured=True, is_active=True).limit(8).all()
    # Only top-level categories on the homepage
    categories = Category.query.filter_by(parent_id=None).all()
    return render_template('index.html', featured_products=featured, categories=categories)

@app.route('/shop')
def shop():
    page = request.args.get('page', 1, type=int)
    category_slug = request.args.get('category', '')
    min_price = request.args.get('min_price', 0, type=float)
    max_price = request.args.get('max_price', 10000, type=float)
    search = request.args.get('search', '')
    query = Product.query.filter_by(is_active=True)
    selected_cat = None
    if category_slug:
        selected_cat = Category.query.filter_by(slug=category_slug).first()
        if selected_cat:
            # Include products from this category AND all its subcategories
            child_ids = [c.id for c in selected_cat.children]
            cat_ids = [selected_cat.id] + child_ids
            query = query.filter(Product.category_id.in_(cat_ids))
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    query = query.filter(Product.price >= min_price, Product.price <= max_price)
    products = query.paginate(page=page, per_page=9)
    # Only top-level categories for the sidebar; children come via .children
    top_categories = Category.query.filter_by(parent_id=None).all()
    return render_template('shop.html', products=products, categories=top_categories,
                           selected_category=category_slug, min_price=min_price,
                           max_price=max_price, search=search)

@app.route('/shop/<category_slug>')
def shop_category(category_slug):
    return redirect(url_for('shop', category=category_slug))

@app.route('/product/<slug>')
def product_detail(slug):
    product = Product.query.filter_by(slug=slug, is_active=True).first_or_404()
    # Increment view count
    product.view_count = (product.view_count or 0) + 1
    db.session.commit()
    related = Product.query.filter_by(category_id=product.category_id, is_active=True).filter(Product.id != product.id).limit(4).all()
    return render_template('product.html', product=product, related_products=related)


@app.route('/api/trending')
def api_trending():
    """Return top 8 trending products (most viewed, falling back to featured) as JSON."""
    products = Product.query.filter_by(is_active=True)\
        .order_by(Product.view_count.desc(), Product.is_featured.desc())\
        .limit(8).all()
    currency = get_currency()
    info = CURRENCIES.get(currency, CURRENCIES['USD'])
    data = []
    for p in products:
        converted = p.price * info['rate']
        data.append({
            'id':        p.id,
            'name':      p.name,
            'slug':      p.slug,
            'price':     f"{info['symbol']}{converted:,.2f}",
            'image_url': p.image_url or '',
            'url':       url_for('product_detail', slug=p.slug),
            'views':     p.view_count or 0,
            'featured':  p.is_featured,
        })
    return jsonify(data)

@app.route('/cart/add', methods=['POST'])
def cart_add():
    product_id = str(request.form.get('product_id'))
    quantity = int(request.form.get('quantity', 1))
    cart = session.get('cart', {})
    cart[product_id] = cart.get(product_id, 0) + quantity
    session['cart'] = cart
    flash('Product added to cart!', 'success')
    return redirect(request.referrer or url_for('shop'))

@app.route('/cart')
def cart():
    items, total = get_cart_items()
    return render_template('cart.html', cart_items=items, total=total)

@app.route('/cart/update', methods=['POST'])
def cart_update():
    product_id = str(request.form.get('product_id'))
    quantity = int(request.form.get('quantity', 1))
    cart = session.get('cart', {})
    if quantity > 0:
        cart[product_id] = quantity
    else:
        cart.pop(product_id, None)
    session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/cart/remove', methods=['POST'])
def cart_remove():
    product_id = str(request.form.get('product_id'))
    cart = session.get('cart', {})
    cart.pop(product_id, None)
    session['cart'] = cart
    flash('Item removed from cart.', 'info')
    return redirect(url_for('cart'))

@app.route('/checkout/escrow-choice', methods=['GET', 'POST'])
def escrow_choice():
    """Ask the buyer whether they want escrow protection before they fill in details."""
    items, total = get_cart_items()
    if not items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('shop'))
    if request.method == 'POST':
        choice = request.form.get('use_escrow', 'no')
        session['use_escrow'] = (choice == 'yes')
        return redirect(url_for('checkout'))
    return render_template('escrow_choice.html', cart_items=items, total=total)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    items, total = get_cart_items()
    if not items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('shop'))
    # If escrow preference not set yet, ask first
    if 'use_escrow' not in session:
        return redirect(url_for('escrow_choice'))
    use_escrow = session.pop('use_escrow', False)
    if request.method == 'POST':
        order_number = generate_order_number()
        while Order.query.filter_by(order_number=order_number).first():
            order_number = generate_order_number()
        payment_method = request.form.get('payment_method', 'BTC')
        order = Order(
            order_number=order_number,
            user_id=current_user.id if current_user.is_authenticated else None,
            name=request.form.get('name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            city=request.form.get('city'),
            country=request.form.get('country'),
            zip_code=request.form.get('zip_code'),
            total=total,
            payment_method=payment_method,
            use_escrow=use_escrow,
            escrow_status='holding' if use_escrow else 'none',
        )
        db.session.add(order)
        db.session.flush()
        for item in items:
            oi = OrderItem(order_id=order.id, product_id=item['product'].id,
                           quantity=item['quantity'], price=item['product'].price)
            db.session.add(oi)
        db.session.commit()
        session['cart'] = {}
        if use_escrow:
            return redirect(url_for('escrow_panel', order_number=order_number))
        return redirect(url_for('order_confirmation', order_number=order_number))
    wallets = {
        'BTC': app.config['BTC_WALLET'],
        'XMR': app.config['XMR_WALLET'],
        'USDT': app.config['USDT_WALLET'],
        'TRX': app.config['TRX_WALLET'],
    }
    return render_template('checkout.html', cart_items=items, total=total,
                           wallets=wallets, use_escrow=use_escrow)

# ---- Escrow routes ----

def _wallet_map():
    return {
        'BTC':  app.config['BTC_WALLET'],
        'XMR':  app.config['XMR_WALLET'],
        'USDT': app.config['USDT_WALLET'],
        'TRX':  app.config['TRX_WALLET'],
    }

@app.route('/escrow/<order_number>')
def escrow_panel(order_number):
    """Escrow payment panel — buyer pays here; funds held until receipt confirmed."""
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    wallets = _wallet_map()
    wallet_address = wallets.get(order.payment_method, app.config['BTC_WALLET'])
    qr_data = generate_qr_code(wallet_address)
    return render_template('escrow_panel.html', order=order,
                           wallet_address=wallet_address, qr_code=qr_data)

@app.route('/escrow/<order_number>/submit-payment', methods=['POST'])
def escrow_submit_payment(order_number):
    """Buyer submits their transaction hash for an escrow order."""
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    order.transaction_hash = request.form.get('transaction_hash', '').strip()
    order.sending_wallet   = request.form.get('sending_wallet', '').strip()
    order.payment_status   = 'submitted'
    db.session.commit()
    flash('Payment proof submitted. Funds will be held in escrow until you confirm receipt.', 'success')
    return redirect(url_for('escrow_panel', order_number=order_number))

@app.route('/escrow/<order_number>/confirm-receipt', methods=['POST'])
def escrow_confirm_receipt(order_number):
    """Buyer confirms they received the goods — releases escrow to vendor."""
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    if order.escrow_status not in ('holding', 'released'):
        flash('This order cannot be confirmed at this stage.', 'warning')
        return redirect(url_for('escrow_panel', order_number=order_number))
    order.buyer_confirmed = True
    order.escrow_status   = 'released'
    order.order_status    = 'delivered'
    order.payment_status  = 'confirmed'
    db.session.commit()
    flash('Thank you! You have confirmed receipt. Payment has been released to the vendor.', 'success')
    return redirect(url_for('escrow_panel', order_number=order_number))

@app.route('/escrow/<order_number>/dispute', methods=['GET', 'POST'])
def escrow_dispute(order_number):
    """Buyer opens a dispute for an escrow order."""
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    if order.escrow_status not in ('holding',):
        flash('A dispute can only be opened while payment is held in escrow.', 'warning')
        return redirect(url_for('escrow_panel', order_number=order_number))
    if order.dispute:
        flash('A dispute already exists for this order.', 'info')
        return redirect(url_for('escrow_panel', order_number=order_number))
    if request.method == 'POST':
        reason = request.form.get('reason', '').strip()
        if not reason:
            flash('Please provide a reason for the dispute.', 'danger')
            return render_template('escrow_dispute.html', order=order)
        image_path = None
        if 'dispute_image' in request.files:
            f = request.files['dispute_image']
            if f and f.filename:
                import uuid, os
                ext = os.path.splitext(f.filename)[1].lower()
                if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
                    flash('Invalid image format. Use JPG, PNG, GIF or WEBP.', 'danger')
                    return render_template('escrow_dispute.html', order=order)
                fname = f'dispute_{order_number}_{uuid.uuid4().hex[:8]}{ext}'
                save_path = os.path.join(app.root_path, 'static', 'uploads', fname)
                f.save(save_path)
                image_path = f'uploads/{fname}'
        dispute = EscrowDispute(
            order_id=order.id,
            reason=reason,
            image_path=image_path,
            status='open',
        )
        order.escrow_status = 'disputed'
        db.session.add(dispute)
        db.session.commit()
        flash('Dispute opened. A moderator will review your case and contact you.', 'success')
        return redirect(url_for('escrow_panel', order_number=order_number))
    return render_template('escrow_dispute.html', order=order)

@app.route('/escrow/<order_number>/dispute/extra-proof', methods=['POST'])
def escrow_dispute_extra_proof(order_number):
    """Buyer submits additional proof requested by admin."""
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    if not order.dispute:
        flash('No dispute found for this order.', 'danger')
        return redirect(url_for('escrow_panel', order_number=order_number))
    order.dispute.extra_proof_submitted = request.form.get('extra_proof', '').strip()
    order.dispute.updated_at = datetime.utcnow()
    db.session.commit()
    flash('Additional proof submitted. The moderator has been notified.', 'success')
    return redirect(url_for('escrow_panel', order_number=order_number))


@app.route('/order/confirmation/<order_number>')
def order_confirmation(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    # Escrow orders live in the escrow panel, not here
    if order.use_escrow:
        return redirect(url_for('escrow_panel', order_number=order_number))
    wallets = _wallet_map()
    wallet_address = wallets.get(order.payment_method, app.config['BTC_WALLET'])
    qr_data = generate_qr_code(wallet_address)
    return render_template('order_confirmation.html', order=order,
                           wallet_address=wallet_address, qr_code=qr_data)

@app.route('/order/tracking', methods=['GET', 'POST'])
def order_tracking():
    order = None
    if request.method == 'POST':
        order_number = request.form.get('order_number', '').strip()
        email = request.form.get('email', '').strip()
        order = Order.query.filter_by(order_number=order_number, email=email).first()
        if not order:
            flash('Order not found. Please check your order number and email.', 'danger')
    return render_template('order_tracking.html', order=order)

@app.route('/order/submit-payment', methods=['POST'])
def submit_payment():
    order_number = request.form.get('order_number')
    transaction_hash = request.form.get('transaction_hash')
    sending_wallet = request.form.get('sending_wallet')
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    order.transaction_hash = transaction_hash
    order.sending_wallet = sending_wallet
    order.payment_status = 'submitted'
    db.session.commit()
    flash('Payment information submitted! We will verify and process your order.', 'success')
    return redirect(url_for('order_confirmation', order_number=order_number))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/how-to-order')
def how_to_order():
    return render_template('how_to_order.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name    = request.form.get('name', '').strip()
        email   = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        # Server-side validation of required fields
        errors = []
        if not name:
            errors.append('Name is required.')
        if not email or '@' not in email:
            errors.append('A valid email address is required.')
        if not subject:
            errors.append('Subject is required.')

        if errors:
            form_data = {'name': name, 'email': email,
                         'subject': subject, 'message': message}
            return render_template('contact.html', form_data=form_data, errors=errors)

        # Success – in production you would send an email here
        return render_template('contact.html',
                               success=True,
                               submitted_name=name,
                               submitted_email=email)

    return render_template('contact.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/auth/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Welcome back!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('Invalid username or password.', 'danger')
    return render_template('auth/login.html')

@app.route('/auth/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return render_template('auth/register.html')
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('auth/register.html')
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Registration successful! Welcome to ShadowHub.', 'success')
        return redirect(url_for('index'))
    return render_template('auth/register.html')

@app.route('/auth/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('dashboard/index.html', orders=orders)

# ---- Admin Routes ----

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/admin/')
@login_required
@admin_required
def admin_index():
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(payment_status='pending').count()
    open_disputes = EscrowDispute.query.filter_by(status='open').count()
    revenue = db.session.query(db.func.sum(Order.total)).filter(Order.payment_status=='confirmed').scalar() or 0
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    return render_template('admin/index.html', total_orders=total_orders,
                           pending_orders=pending_orders, revenue=revenue,
                           open_disputes=open_disputes,
                           recent_orders=recent_orders)

@app.route('/admin/products')
@login_required
@admin_required
def admin_products():
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('admin/products.html', products=products)

@app.route('/admin/products/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_product():
    top_categories = Category.query.filter_by(parent_id=None).order_by(Category.name).all()
    if request.method == 'POST':
        name = request.form.get('name')
        slug = request.form.get('slug') or name.lower().replace(' ', '-')
        product = Product(
            name=name, slug=slug,
            description=request.form.get('description'),
            price=float(request.form.get('price', 0)),
            stock=int(request.form.get('stock', 0)),
            category_id=request.form.get('category_id') or None,
            image_url=request.form.get('image_url'),
            is_featured=bool(request.form.get('is_featured')),
            is_active=bool(request.form.get('is_active', True)),
        )
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin/add_product.html', top_categories=top_categories, product=None)

@app.route('/admin/products/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_product(id):
    product = Product.query.get_or_404(id)
    top_categories = Category.query.filter_by(parent_id=None).order_by(Category.name).all()
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.slug = request.form.get('slug') or product.name.lower().replace(' ', '-')
        product.description = request.form.get('description')
        product.price = float(request.form.get('price', 0))
        product.stock = int(request.form.get('stock', 0))
        product.category_id = request.form.get('category_id') or None
        product.image_url = request.form.get('image_url')
        product.is_featured = bool(request.form.get('is_featured'))
        product.is_active = bool(request.form.get('is_active'))
        db.session.commit()
        flash('Product updated!', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin/add_product.html', product=product, top_categories=top_categories)

@app.route('/admin/products/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted.', 'info')
    return redirect(url_for('admin_products'))

@app.route('/admin/orders')
@login_required
@admin_required
def admin_orders():
    status_filter = request.args.get('status', '')
    query = Order.query.order_by(Order.created_at.desc())
    if status_filter:
        query = query.filter_by(payment_status=status_filter)
    orders = query.all()
    return render_template('admin/orders.html', orders=orders, status_filter=status_filter)

@app.route('/admin/orders/<order_number>')
@login_required
@admin_required
def admin_order_detail(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    return render_template('admin/order_detail.html', order=order)

@app.route('/admin/orders/<order_number>/confirm', methods=['POST'])
@login_required
@admin_required
def admin_confirm_order(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    order.payment_status = 'confirmed'
    order.order_status = 'processing'
    db.session.commit()
    flash('Payment confirmed!', 'success')
    return redirect(url_for('admin_order_detail', order_number=order_number))

@app.route('/admin/orders/<order_number>/update-status', methods=['POST'])
@login_required
@admin_required
def admin_update_order_status(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    order.order_status = request.form.get('order_status', order.order_status)
    db.session.commit()
    flash('Order status updated!', 'success')
    return redirect(url_for('admin_order_detail', order_number=order_number))

@app.route('/admin/categories')
@login_required
@admin_required
def admin_categories():
    top_categories = Category.query.filter_by(parent_id=None).order_by(Category.name).all()
    return render_template('admin/categories.html', top_categories=top_categories)

@app.route('/admin/categories/add', methods=['POST'])
@login_required
@admin_required
def admin_add_category():
    name = request.form.get('name')
    slug = request.form.get('slug') or name.lower().replace(' ', '-').replace(' ', '-')
    description = request.form.get('description')
    parent_id = request.form.get('parent_id') or None
    cat = Category(name=name, slug=slug, description=description, parent_id=parent_id)
    db.session.add(cat)
    db.session.commit()
    flash('Category added!', 'success')
    return redirect(url_for('admin_categories'))

@app.route('/admin/categories/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_category(id):
    cat = Category.query.get_or_404(id)
    db.session.delete(cat)
    db.session.commit()
    flash('Category deleted.', 'info')
    return redirect(url_for('admin_categories'))


@app.route('/admin/orders/<order_number>/escrow-action', methods=['POST'])
@login_required
@admin_required
def admin_escrow_action(order_number):
    """Admin releases or refunds escrow, or requests more proof from buyer."""
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    action = request.form.get('action')
    if action == 'release':
        order.escrow_status  = 'released'
        order.payment_status = 'confirmed'
        order.order_status   = 'delivered'
        if order.dispute:
            order.dispute.status = 'resolved_release'
        db.session.commit()
        flash('Escrow released — funds sent to vendor.', 'success')
    elif action == 'refund':
        order.escrow_status  = 'refunded'
        order.payment_status = 'refunded'
        order.order_status   = 'cancelled'
        if order.dispute:
            order.dispute.status = 'resolved_refund'
        db.session.commit()
        flash('Escrow refunded — funds returned to buyer.', 'success')
    elif action == 'request_proof':
        if order.dispute:
            order.dispute.extra_proof_requested = True
            order.dispute.extra_proof_message   = request.form.get('proof_message', '').strip()
            order.dispute.status = 'under_review'
            db.session.commit()
            flash('Additional proof requested from buyer.', 'info')
    elif action == 'add_notes':
        if order.dispute:
            order.dispute.admin_notes = request.form.get('admin_notes', '').strip()
            order.dispute.status = 'under_review'
            db.session.commit()
            flash('Admin notes saved.', 'info')
    return redirect(url_for('admin_order_detail', order_number=order_number))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_sample_data()
    app.run(debug=True)
