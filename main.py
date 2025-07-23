from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'semblnyce_secret_key_2024'

# Initialize view counter
VIEW_COUNT_FILE = 'view_count.json'
DONATIONS_FILE = 'donations.json'

def load_view_count():
    if os.path.exists(VIEW_COUNT_FILE):
        with open(VIEW_COUNT_FILE, 'r') as f:
            return json.load(f)
    return {'total': 0, 'pages': {}}

def save_view_count(data):
    with open(VIEW_COUNT_FILE, 'w') as f:
        json.dump(data, f)

def load_donations():
    if os.path.exists(DONATIONS_FILE):
        with open(DONATIONS_FILE, 'r') as f:
            return json.load(f)
    return {'total': 12847}

def save_donations(data):
    with open(DONATIONS_FILE, 'w') as f:
        json.dump(data, f)

def increment_view(page):
    data = load_view_count()
    data['total'] += 1
    if page not in data['pages']:
        data['pages'][page] = 0
    data['pages'][page] += 1
    save_view_count(data)

# Sample data
PRODUCTS = [
    {
        'id': '1',
        'name': 'RIOT HEART TEE',
        'price': 45,
        'image': 'riot-heart.jpg',
        'designer_id': '1'
    },
    {
        'id': '2',
        'name': 'STREET GHOST HOODIE',
        'price': 85,
        'image': 'street-ghost.jpg',
        'designer_id': '2'
    },
    {
        'id': '3',
        'name': 'NEON REBELLION TANK',
        'price': 35,
        'image': 'neon-rebellion.jpg',
        'designer_id': '3'
    },
]

DESIGNERS = {
    '1': {
        'name': 'MARCUS "SKETCH" WILLIAMS',
        'bio': 'Marcus has been creating art on the streets for over a decade. His designs capture the raw energy of urban life, transforming personal struggle into powerful visual statements. Currently living at the Bowery Mission, Marcus uses art as both expression and survival.',
        'video_url': 'https://www.youtube.com/embed/dQw4w9WgXcQ',
        'support_link': 'https://gofundme.com/marcus-sketch-williams'
    },
    '2': {
        'name': 'ARIA "PHANTOM" CHEN',
        'bio': 'Known for her haunting designs that blend street art with traditional techniques, Aria creates from her tent community in Echo Park. Her work explores themes of invisibility and presence in urban spaces.',
        'video_url': 'https://www.youtube.com/embed/dQw4w9WgXcQ',
        'support_link': 'https://gofundme.com/aria-phantom-chen'
    },
    '3': {
        'name': 'JEROME "VOLT" JACKSON',
        'bio': 'A self-taught artist who found his voice through graffiti, Jerome channels the electric energy of the city into explosive designs. Living rough for three years, he sees each piece as a declaration of existence.',
        'video_url': None,
        'support_link': 'https://gofundme.com/jerome-volt-jackson'
    }
}

# Routes
@app.route('/')
def home():
    increment_view('home')
    return render_template('home.html')

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
    return render_template('product.html', product=product)

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

    # Log contact form submission
    print(f"Contact form submission: {name}, {email}, {message}")

    # Save to file for Replit (since email might not work)
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

    return jsonify({
        'success': True,
        'message': 'Message received! We\'ll get back to you soon.'
    })

@app.route('/donate')
def donate():
    increment_view('donate')
    donations = load_donations()
    return render_template('donate.html', total_raised=donations['total'])

@app.route('/process_donation', methods=['POST'])
def process_donation():
    data = request.json
    amount = float(data.get('amount', 0))

    if amount > 0:
        donations = load_donations()
        donations['total'] += amount
        save_donations(donations)

        return jsonify({
            'success': True,
            'new_total': donations['total']
        })

    return jsonify({'success': False})

@app.route('/admin/views')
def admin_views():
    view_data = load_view_count()
    return render_template('admin.html', view_data=view_data)

@app.route('/admin/contacts')
def admin_contacts():
    contacts = []
    if os.path.exists('contacts.json'):
        with open('contacts.json', 'r') as f:
            contacts = json.load(f)
    return render_template('admin_contacts.html', contacts=contacts)

if __name__ == '__main__':
    # Create templates and static directories if they don't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)

    print("Server starting...")
    print("Visit your Replit URL to see the website")
    print("Admin panel: /admin/views")
    print("Contact submissions: /admin/contacts")

    # Replit requires host='0.0.0.0' and port=5000
    app.run(host='0.0.0.0', port=5000, debug=True)