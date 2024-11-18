from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from models import db, User, Package, Subscription, Order
from config import Config
from datetime import timedelta
from flask_cors import CORS
from flask_migrate import Migrate
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
CORS(app)
app.config.from_object(Config)
db.init_app(app)
migrate = Migrate(app, db)

jwt = JWTManager(app)

def create_tables():
    with app.app_context():
        db.create_all()



SMTP_SERVER = 'smtp.gmail.com'  # Replace with your SMTP server
SMTP_PORT = 587  # Replace with your SMTP port
SENDER_EMAIL = 'briimiin@gmail.com'
SENDER_PASSWORD = 'lpps ohjg ievj ijgm'

# Temporary modified User Registration route to allow setting admin status
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    is_admin = data.get('is_admin', False)  # Allow setting admin status
    user = User(username=data['username'], email=data['email'], is_admin=is_admin)
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    return jsonify(message="User registered successfully"), 201

# User Login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    if user and user.check_password(data['password']):
        access_token = create_access_token(identity=user.id, expires_delta=timedelta(hours=1))
        return jsonify(access_token=access_token)
    return jsonify(message="Invalid credentials"), 401

# View user profile
@app.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    current_user = User.query.get(get_jwt_identity())
    return jsonify({
        "username": current_user.username,
        "email": current_user.email,
        "is_admin": current_user.is_admin
    }), 200

# Update user profile
@app.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    current_user = User.query.get(get_jwt_identity())
    data = request.get_json()
    if 'username' in data:
        current_user.username = data['username']
    if 'email' in data:
        current_user.email = data['email']
    db.session.commit()
    return jsonify(message="Profile updated successfully"), 200

# View Packages
@app.route('/packages', methods=['GET'])
def get_packages():
    packages = Package.query.all()
    return jsonify([{
        "id": p.id,
        "name": p.name,
        "speed": p.speed,
        "price": p.price,
        "description": p.description
    } for p in packages])

# Admin: Add a Package
@app.route('/packages', methods=['POST'])
@jwt_required()
def add_package():
    data = request.get_json()
    package = Package(name=data['name'], speed=data['speed'], price=data['price'], description=data.get('description'))
    db.session.add(package)
    db.session.commit()
    return jsonify(message="Package added successfully"), 201

# Admin: Update a Package
@app.route('/packages/<int:package_id>', methods=['PUT'])
@jwt_required()
def update_package(package_id):
    data = request.get_json()
    package = Package.query.get_or_404(package_id)
    package.name = data.get('name', package.name)
    package.speed = data.get('speed', package.speed)
    package.price = data.get('price', package.price)
    package.description = data.get('description', package.description)
    db.session.commit()
    return jsonify(message="Package updated successfully"), 200

# Admin: Delete a Package
@app.route('/packages/<int:package_id>', methods=['DELETE'])
@jwt_required()
def delete_package(package_id):
    package = Package.query.get_or_404(package_id)
    db.session.delete(package)
    db.session.commit()
    return jsonify(message="Package deleted successfully"), 200
@app.route('/subscribe', methods=['POST'])
def subscribe():
    data = request.get_json()

    # Extract fields from request data
    package_id = data.get('package_id')
    area_of_residence = data.get('area_of_residence')
    phone_number = data.get('phone_number')
    email = data.get('email')
    house_number = data.get('house_number')

    # Validate required fields
    if not all([package_id, area_of_residence, phone_number, email, house_number]):
        return jsonify({"error": "All fields are required"}), 400

    # Retrieve package details
    package = Package.query.get(package_id)
    if not package:
        return jsonify({"error": "Package not found"}), 404

    # Create new Subscription entry
    new_subscription = Subscription(
        package_id=package_id,
        area_of_residence=area_of_residence,
        phone_number=phone_number,
        email=email,
        house_number=house_number,
    )

    try:
        db.session.add(new_subscription)
        db.session.commit()

        # Send confirmation email with package details
        send_confirmation_email(email, package, area_of_residence, phone_number, house_number)

        return jsonify({"message": "Subscription successful!"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

def send_confirmation_email(to_email, package, area_of_residence, phone_number, house_number):
    # Create the email content
    subject = "Subscription Confirmation"
    body = f"""
    Thank you for subscribing to our {package.name} package!

    Subscription Details:
    - Package Name: {package.name}
    - Speed: {package.speed} Mbps
    - Price: {package.price} per month
    - Area of Residence: {area_of_residence}
    - Phone Number: {phone_number}
    - House Number: {house_number}

    Payment Information:
    - Please send payment to 0711103774.
    - Contact our support team if you have any questions.

    Thank you for choosing our services!
    """

    # Setup the email
    message = MIMEMultipart()
    message['From'] = SENDER_EMAIL
    message['To'] = to_email
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    # Send the email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, message.as_string())
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")


# View Orders
@app.route('/orders', methods=['GET'])
@jwt_required()
def get_orders():
    orders = Order.query.all()
    return jsonify([{
        "id": o.id,
        "user_id": o.user_id,
        "product_name": o.product_name,
        "order_date": o.order_date,
        "status": o.status
    } for o in orders])

# Place an Order
@app.route('/order', methods=['POST'])
@jwt_required()
def place_order():
    data = request.get_json()
    order = Order(user_id=get_jwt_identity(), product_name=data['product_name'])
    db.session.add(order)
    db.session.commit()
    return jsonify(message="Order placed successfully"), 201


# View billing history
@app.route('/billing', methods=['GET'])
@jwt_required()
def view_billing():
    user_id = get_jwt_identity()
    orders = Order.query.filter_by(user_id=user_id).all()
    return jsonify([{
        "id": order.id,
        "product_name": order.product_name,
        "order_date": order.order_date,
        "status": order.status
    } for order in orders]), 200

# Payment Processing (mockup)
@app.route('/payment', methods=['POST'])
@jwt_required()
def process_payment():
    data = request.get_json()
    # Mock processing (you'd integrate with an actual payment processor here)
    return jsonify(message="Payment processed successfully"), 200

# Admin: Update Order Status
@app.route('/orders/<int:order_id>', methods=['PUT'])
@jwt_required()
def update_order_status(order_id):
    data = request.get_json()
    order = Order.query.get_or_404(order_id)
    order.status = data.get('status', order.status)
    db.session.commit()
    return jsonify(message="Order status updated successfully"), 200


# Helper function to check if the current user is an admin
def is_admin():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return user.is_admin if user else False

# Admin: View All Subscriptions
@app.route('/admin/subscriptions', methods=['GET'])
@jwt_required()
def admin_get_subscriptions():
    if not is_admin():
        return jsonify(message="Admin access required"), 403
    
    subscriptions = Subscription.query.all()
    return jsonify([{
        "id": sub.id,
        "user_id": sub.user_id,
        "package_id": sub.package_id,
        "subscription_date": sub.start_date
    } for sub in subscriptions]), 200

# Admin: Record a Sale for a User
@app.route('/admin/sales', methods=['POST'])
@jwt_required()
def record_sale():
    if not is_admin():
        return jsonify(message="Admin access required"), 403
    
    data = request.get_json()
    order = Order(user_id=data['user_id'], product_name=data['product_name'], status="completed")
    db.session.add(order)
    db.session.commit()
    return jsonify(message="Sale recorded successfully"), 201

# Admin: View Sales Analytics
@app.route('/admin/analytics', methods=['GET'])
@jwt_required()
def admin_analytics():
    if not is_admin():
        return jsonify(message="Admin access required"), 403
    
    total_sales = Order.query.count()
    total_subscriptions = Subscription.query.count()
    active_subscriptions = Subscription.query.filter(Subscription.is_active == "active").count()
    
    return jsonify({
        "total_sales": total_sales,
        "total_subscriptions": total_subscriptions,
        "active_subscriptions": active_subscriptions
    }), 200
if __name__ == '__main__':
    create_tables()
    app.run(debug=True)