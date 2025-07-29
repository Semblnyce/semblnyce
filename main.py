from flask import Flask, render_template, request, jsonify, redirect, url_for, session, make_response
from flask_mail import Mail, Message
import os
import stripe
import json
from datetime import datetime, timedelta
import uuid
import hashlib

app = Flask(__name__)
app.secret_key = 'semblnyce_secret_key_2024'

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')

# Admin email addresses - only these can access admin panel
ADMIN_EMAILS = [
    'semblnyce@gmail.com',
    'rahibh2010@gmail.com',  
    'brandonho1957@gmail.com',
    'jboateng.p937@prepforprep.org',
    'rhoque.pf44@prepforprep.org',
    'ife2025.team3@gmail.com'# Add your admin emails here
]

# === Email Configuration ===
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'semblnyce@gmail.com'
app.config['MAIL_PASSWORD'] = 'qzrk zwwo vquc rtyk'
app.config['MAIL_DEFAULT_SENDER'] = 'semblnyce@gmail.com'

mail = Mail(app)

# Initialize files
VIEW_COUNT_FILE = 'view_count.json'
ANALYTICS_FILE = 'analytics.json'
ORDERS_FILE = 'orders.json'

def load_json_file(filename, default):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return default

def save_json_file(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def load_view_count():
    return load_json_file(VIEW_COUNT_FILE, {'total': 0, 'pages': {}})

def save_view_count(data):
    save_json_file(VIEW_COUNT_FILE, data)

def load_analytics():
    return load_json_file(ANALYTICS_FILE, {
        'unique_visitors': {},  # Changed to dict to store email->user_id mapping
        'returning_users': [],
        'daily_views': {},
        'total_revenue': 0
    })

def save_analytics(data):
    save_json_file(ANALYTICS_FILE, data)

def load_orders():
    return load_json_file(ORDERS_FILE, [])

def save_orders(data):
    save_json_file(ORDERS_FILE, data)

def get_user_identifier():
    """Get user identifier from Google email or fallback to session ID"""
    if 'google_email' in session:
        return session['google_email']
    elif 'user_id' in session:
        return session['user_id']
    else:
        session['user_id'] = str(uuid.uuid4())
        return session['user_id']

def track_visitor():
    """Track visitor analytics"""
    if 'cookies_accepted' not in request.cookies:
        return  # Don't track if cookies not accepted

    user_identifier = get_user_identifier()
    analytics = load_analytics()
    today = datetime.now().strftime('%Y-%m-%d')

    # Track unique visitors
    if user_identifier not in analytics['unique_visitors']:
        analytics['unique_visitors'][user_identifier] = {
            'first_visit': today,
            'visit_count': 1
        }
    else:
        # Track returning users
        analytics['unique_visitors'][user_identifier]['visit_count'] += 1
        if user_identifier not in analytics['returning_users']:
            analytics['returning_users'].append(user_identifier)

    # Track daily views
    if today not in analytics['daily_views']:
        analytics['daily_views'][today] = 0
    analytics['daily_views'][today] += 1

    save_analytics(analytics)

def increment_view(page):
    """Increment page view count"""
    data = load_view_count()
    data['total'] += 1
    if page not in data['pages']:
        data['pages'][page] = 0
    data['pages'][page] += 1
    save_view_count(data)

    # Track visitor analytics
    track_visitor()

# Sample data with sizes
PRODUCTS = [
    {
        'id': '1',
        'name': 'RIOT HEART TEE',
        'price': 45,
        'image': '🔥',
        'designer_id': '1',
        'description': 'This piece represents the raw energy of street culture, designed by one of our featured artists experiencing homelessness. Made from premium cotton with a bold graphic that speaks to the heart of urban rebellion.',
        'sizes': ['S', 'M', 'L', 'XL', 'XXL']
    },
    {
        'id': '2',
        'name': 'STREET GHOST HOODIE',
        'price': 85,
        'image': '👻',
        'designer_id': '2',
        'description': 'A haunting design that captures the invisible struggles of city life. This premium hoodie features unique artwork that tells the story of those who walk unseen through urban landscapes.',
        'sizes': ['S', 'M', 'L', 'XL', 'XXL']
    },
    {
        'id': '3',
        'name': 'NEON REBELLION TANK',
        'price': 35,
        'image': '⚡',
        'designer_id': '3',
        'description': 'Electric energy meets street fashion in this bold tank top. Perfect for those who want to make a statement while supporting artists in need.',
        'sizes': ['S', 'M', 'L', 'XL']
    },
]

DESIGNERS = {
    '1': {
        'name': 'MARCUS "SKETCH" WILLIAMS',
        'bio': 'Marcus has been creating art on the streets for over a decade. His designs capture the raw energy and emotion of urban life, transforming pain into powerful visual statements. Born and raised in downtown LA, Marcus found solace in art during his most challenging times. His work reflects the struggle and resilience of those living on the margins of society.',
        'image': '🎨',  # Placeholder - replace with actual image path
        'video_url': 'https://www.youtube.com/embed/dQw4w9WgXcQ',
        'support_link': 'https://gofundme.com/marcus-sketch-williams'
    },
    '2': {
        'name': 'ARIA "PHANTOM" CHEN',
        'bio': 'Known for her haunting designs that blend Eastern philosophy with Western street culture, Aria creates pieces that speak to the invisible struggles of urban existence. After losing her apartment due to rising rent costs, Aria channeled her experiences into powerful artistic expressions that bridge cultural divides and illuminate hidden truths.',
        'image': '👤',  # Placeholder - replace with actual image path
        'video_url': 'https://www.youtube.com/embed/Ec18vXsDHYU?si=inAoOSskFf69_J6Y',
        'support_link': 'https://gofundme.com/aria-phantom-chen'
    },
    '3': {
        'name': 'JEROME "VOLT" JACKSON',
        'bio': 'A self-taught artist who found his voice through adversity, Jerome\'s electric designs pulse with the heartbeat of the city streets. Growing up in foster care and later experiencing homelessness, Jerome uses his art to process trauma and inspire hope. His work captures the electric energy of survival and the power of human resilience.',
        'image': '⚡',  # Placeholder - replace with actual image path
        'video_url': None,
        'support_link': 'https://gofundme.com/jerome-volt-jackson'
    }
}

def is_admin():
    """Check if current user is admin"""
    return session.get('google_email') in ADMIN_EMAILS

# Routes
@app.route('/')
def home():
    increment_view('home')
    show_cookie_banner = 'cookies_accepted' not in request.cookies
    return render_template('home.html', show_cookie_banner=show_cookie_banner)

@app.route('/accept_cookies', methods=['POST'])
def accept_cookies():
    response = jsonify({'success': True})
    response.set_cookie('cookies_accepted', 'true', max_age=365*24*60*60)  # 1 year
    return response

@app.route('/deny_cookies', methods=['POST'])
def deny_cookies():
    response = jsonify({'success': True})
    response.set_cookie('cookies_denied', 'true', max_age=365*24*60*60)  # 1 year
    return response

@app.route('/google_signin', methods=['POST'])
def google_signin():
    """Handle Google sign-in"""
    data = request.json
    email = data.get('email')
    if email:
        session['google_email'] = email
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/shop')
def shop():
    increment_view('shop')
    return render_template('shop.html', products=PRODUCTS)

@app.route('/product/<product_id>')
def product(product_id):
    increment_view(f'product_{product_id}')
    product = next((p for p in PRODUCTS if p['id'] == product_id), None)
    if not product:
        return redirect(url_for('shop'))
    return render_template('product.html', product=product, stripe_public_key=STRIPE_PUBLISHABLE_KEY)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    data = request.json
    product_id = data.get('product_id')
    size = data.get('size', 'M')  # Default to Medium
    quantity = int(data.get('quantity', 1))

    if 'cart' not in session:
        session['cart'] = []

    product = next((p for p in PRODUCTS if p['id'] == product_id), None)
    if product:
        # Check if same product and size already in cart
        cart_item = next((item for item in session['cart'] 
                         if item['id'] == product_id and item['size'] == size), None)
        if cart_item:
            cart_item['quantity'] += quantity
        else:
            session['cart'].append({
                'id': product['id'],
                'name': product['name'],
                'price': product['price'],
                'image': product['image'],
                'size': size,
                'quantity': quantity
            })
        session.modified = True
        return jsonify({
            'success': True, 
            'cart_count': sum(item['quantity'] for item in session['cart'])
        })

    return jsonify({'success': False})

@app.route('/cart')
def cart():
    increment_view('cart')
    cart_items = session.get('cart', [])
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/update_cart', methods=['POST'])
def update_cart():
    data = request.json
    product_id = data.get('product_id')
    size = data.get('size')
    action = data.get('action')

    if 'cart' in session:
        cart_item = next((item for item in session['cart'] 
                         if item['id'] == product_id and item['size'] == size), None)
        if cart_item:
            if action == 'increase':
                cart_item['quantity'] += 1
            elif action == 'decrease' and cart_item['quantity'] > 1:
                cart_item['quantity'] -= 1
            elif action == 'remove':
                session['cart'] = [item for item in session['cart'] 
                                 if not (item['id'] == product_id and item['size'] == size)]

            session.modified = True
            return jsonify({'success': True})

    return jsonify({'success': False})

@app.route('/create-payment-intent', methods=['POST'])
def create_payment_intent():
    try:
        data = request.json
        cart_items = session.get('cart', [])

        if not cart_items:
            return jsonify({'error': 'Cart is empty'}), 400

        amount = sum(item['price'] * item['quantity'] for item in cart_items)

        # Create a PaymentIntent with Stripe
        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),  # Amount in cents
            currency='usd',
            metadata={
                'user_id': get_user_identifier(),
                'items': json.dumps([{
                    'name': item['name'],
                    'size': item['size'],
                    'quantity': item['quantity'],
                    'price': item['price']
                } for item in cart_items])
            }
        )

        return jsonify({
            'clientSecret': intent['client_secret']
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 403

@app.route('/payment-success', methods=['POST'])
def payment_success():
    try:
        cart_items = session.get('cart', [])
        if not cart_items:
            return jsonify({'success': False, 'message': 'Cart is empty'})

        total = sum(item['price'] * item['quantity'] for item in cart_items)
        user_identifier = get_user_identifier()

        # Record the order
        orders = load_orders()
        order = {
            'id': str(uuid.uuid4()),
            'user_id': user_identifier,
            'customer_email': session.get('google_email', 'Unknown'),
            'items': cart_items.copy(),
            'total': total,
            'timestamp': datetime.now().isoformat(),
            'status': 'completed'
        }
        orders.append(order)
        save_orders(orders)

        # Update analytics
        analytics = load_analytics()
        analytics['total_revenue'] += total
        save_analytics(analytics)

        # Clear cart
        session['cart'] = []
        session.modified = True

        return jsonify({'success': True, 'message': 'Order placed successfully!'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/designer/<designer_id>')
def designer(designer_id):
    increment_view(f'designer_{designer_id}')
    designer_info = DESIGNERS.get(designer_id)
    if not designer_info:
        return redirect(url_for('shop'))
    return render_template('designer.html', designer=designer_info)

@app.route('/about')
def about():
    increment_view('about')
    return render_template('about.html')

@app.route('/contact')
def contact():
    increment_view('contact')
    return render_template('contact.html')

@app.route('/submit_contact', methods=['POST'])
def submit_contact():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    message = data.get('message')

    # Save contact info to file
    contacts_file = 'contacts.json'
    contacts = []
    if os.path.exists(contacts_file):
        with open(contacts_file, 'r') as f:
            contacts = json.load(f)

    contacts.append({
        'name': name,
        'email': email,
        'message': message,
        'timestamp': datetime.now().isoformat()
    })

    with open(contacts_file, 'w') as f:
        json.dump(contacts, f, indent=2)

    # Send emails
    try:
        # Email to admin
        msg_to_admin = Message(
            subject=f"New Contact Form Submission from {name}",
            recipients=['semblnyce@gmail.com'],
            body=f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
        )
        mail.send(msg_to_admin)

        # Confirmation email to sender
        msg_to_user = Message(
            subject="Thanks for contacting Semblnyce!",
            recipients=[email],
            body=f"Hi {name},\n\nThanks for reaching out to us. We've received your message and will get back to you shortly.\n\nHere's what you sent:\n\n{message}\n\n– The Semblnyce Team"
        )
        mail.send(msg_to_user)

    except Exception as e:
        print("Email sending failed:", e)

    return jsonify({'success': True, 'message': 'Message received! We\'ll get back to you soon.'})

# Admin routes
@app.route('/admin/dashboard')
def admin_dashboard():
    if not is_admin():
        return redirect(url_for('home'))

    view_data = load_view_count()
    analytics = load_analytics()
    orders = load_orders()

    # Calculate today's views
    today = datetime.now().strftime('%Y-%m-%d')
    today_views = analytics['daily_views'].get(today, 0)

    # Get unique visitors count
    unique_visitors = len(analytics['unique_visitors'])

    # Get returning users count
    returning_users = len(analytics['returning_users'])

    # Get total revenue
    total_revenue = analytics['total_revenue']

    # Get recent orders
    recent_orders = sorted(orders, key=lambda x: x['timestamp'], reverse=True)[:10]

    return render_template('admin_dashboard.html', 
                         view_data=view_data,
                         today_views=today_views,
                         unique_visitors=unique_visitors,
                         returning_users=returning_users,
                         total_revenue=total_revenue,
                         recent_orders=recent_orders,
                         total_orders=len(orders))

@app.route('/admin/orders')
def admin_orders():
    if not is_admin():
        return redirect(url_for('home'))

    orders = load_orders()
    orders = sorted(orders, key=lambda x: x['timestamp'], reverse=True)

    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/contacts')
def admin_contacts():
    if not is_admin():
        return redirect(url_for('home'))

    contacts = []
    if os.path.exists('contacts.json'):
        with open('contacts.json', 'r') as f:
            contacts = json.load(f)

    contacts = sorted(contacts, key=lambda x: x['timestamp'], reverse=True)
    return render_template('admin_contacts.html', contacts=contacts)

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)

    print("Server starting...")
    print("Visit your Replit URL to see the website")
    print("Admin dashboard: /admin/dashboard")
    print("Admin orders: /admin/orders")
    print("Contact submissions: /admin/contacts")

    app.run(host='0.0.0.0', port=5000, debug=True)