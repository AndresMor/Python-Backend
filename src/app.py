from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from flask_marshmallow import Marshmallow
from marshmallow import fields, validate, ValidationError
import os


load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
ma = Marshmallow(app)

#Models
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(10), unique=True, nullable=False)
    address = db.Column(db.String(80), nullable=False)
    nationality = db.Column(db.String(80), nullable=False)
    orders = db.relationship('Order', backref='customer', lazy='joined')

    def __init__(self, name, email, phone, address, nationality):
        self.name = name
        self.email = email
        self.phone = phone
        self.address = address
        self.nationality = nationality

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'),nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    state = db.Column(db.String(80), nullable=False)
    items = db.relationship('Item', backref='order', lazy='joined')

    def __init__(self, customer_id, date, state, customer):
        self.customer_id = customer_id
        self.date = date
        self.state = state
        self.customer = customer
        self.items = []

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'),nullable=False)
    width = db.Column(db.Float, nullable=False)
    length = db.Column(db.Float, nullable=False)

    def __init__(self, order_id, width, length, order):
        self.order_id = order_id
        self.width = width
        self.length = length
        self.order = order


db.create_all()

#Schemas
class CustomerSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'email', 'phone', 'address', 'nationality')
        include_fk = True

    name = fields.String(required=True, validate=validate.Length(min=3))
    email = fields.Email()
    phone = fields.String(required=True, validate=validate.Length(min=10))
    address = fields.String(required=True)
    nationality = fields.String(required=True)



class OrderSchema(ma.Schema):
    class Meta:
        fields = ('id', 'customer_id', 'date', 'state', 'customer')
        include_fk = True
    
    customer = ma.Nested(CustomerSchema)
    date = fields.Date(format='%Y-%m-%d', required=True)

class ItemSchema(ma.Schema):
    class Meta:
        fields = ('id', 'order_id', 'width', 'length', 'order')
        include_fk = True
    
    order = ma.Nested(OrderSchema)
    width = fields.Float(required=True)
    length = fields.Float(required=True)

class OrderItemsSchema(ma.Schema):
    class Meta:
        fields = ('id', 'customer_id', 'date', 'state', 'items')
        include_fk = True
    
    items = ma.Nested(ItemSchema, many=True)

customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)

order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)

item_schema = ItemSchema()
orderItems_schema = OrderItemsSchema()


#Endpoints
@app.route('/customers', methods=['POST'])
def create_customer():

    try:
        customer_schema.load(request.json)
    except ValidationError as err:
        return make_response(jsonify({"message": 'bad request', "error": err.messages}), 400)

    if Customer.query.filter(Customer.email==request.json['email']).first() is not None:
        return make_response(jsonify({"message": 'bad request', "error": 'user with this email already exists'}), 400)

    if Customer.query.filter(Customer.phone==request.json['phone']).first() is not None:
        return make_response(jsonify({"message": 'bad request', "error": 'user with this phone already exists'}), 400)

    name = request.json['name']
    email = request.json['email']
    phone = request.json['phone']
    address = request.json['address']
    nationality = request.json['nationality']

    new_customer = Customer(name,email,phone,address,nationality)
    db.session.add(new_customer)
    db.session.commit()

    return customer_schema.jsonify(new_customer)
    


@app.route('/customers', methods=['GET'])
def get_customers():
    all_customers = Customer.query.all()
    response = customers_schema.dump(all_customers)
    return jsonify(response)

@app.route('/customers/<id>', methods=['PUT'])
def update_customer(id):
    customer = Customer.query.filter_by(id=id).first()
    if customer is None:
         return make_response(jsonify({"message": 'bad request', "error": 'user not found'}), 400)

    try:
        customer_schema.load(request.json, partial=True)
    except ValidationError as err:
        return make_response(jsonify({"message": 'bad request', "error": err.messages}), 400)

    for attr, val in request.json.items():
        if not attr == 'id':
            setattr(customer, attr, val)

    db.session.commit()
    return customer_schema.jsonify(customer)
    
@app.route('/customers/<id>', methods=['DELETE'])
def delete_customer(id):
    customer = Customer.query.filter_by(id=id).first()
    if customer is None:
         return make_response(jsonify({"message": 'bad request', "error": 'user not found'}), 400)

    db.session.delete(customer)
    db.session.commit()
    return customer_schema.jsonify(customer)

@app.route('/order/<id>', methods=['POST'])
def create_order(id):
    customer = Customer.query.filter_by(id=id).first()
    if customer is None:
         return make_response(jsonify({"message": 'bad request', "error": 'user not found'}), 400)

    try:
        order_schema.load(request.json)
    except ValidationError as err:
        return make_response(jsonify({"message": 'bad request', "error": err.messages}), 400)
    
    customer_id = id
    date = request.json['date']
    state = "Solicitada"
    new_order = Order(customer_id, date, state, customer)
    db.session.add(new_order)
    db.session.commit()
    return order_schema.jsonify(new_order)

@app.route('/orders', methods=['GET'])
def get_orders():
    all_orders = Order.query.all()
    response = orders_schema.dump(all_orders)
    return jsonify(response)    

@app.route('/order/<id>/<sw>', methods=['PUT'])
def update_order(id, sw):
    order = Order.query.filter_by(id=id).first()
    if order is None:
         return make_response(jsonify({"message": 'bad request', "error": 'order not found'}), 400)
    
    if sw == "1": 
        order.state = "Aprobada"
    elif sw == "0":
        order.state = "Anulada"
    else:
        response = make_response(jsonify({"message": 'bad request', "error": "param error"}), 400)
        return response   

    db.session.commit()
    return order_schema.jsonify(order)


@app.route('/item/<id>', methods=['POST'])
def create_item(id):

    order = Order.query.filter_by(id=id).first()
    if order is None:
         return make_response(jsonify({"message": 'bad request', "error": 'order not found'}), 400)

    try:
        item_schema.load(request.json)
    except ValidationError as err:
        return make_response(jsonify({"message": 'bad request', "error": err.messages}), 400)

    if order.state != "Solicitada":
        return make_response(jsonify({"message": 'bad request', "error": 'order probably approved or rejected, you cannot add items'}), 400)

    order_id = id
    width = request.json['width']
    length = request.json['length']
    new_item = Item(order_id, width, length, order)
    db.session.add(new_item)
    db.session.commit()
    return item_schema.jsonify(new_item)

@app.route('/order/<id>', methods=['GET'])
def get_order(id):
    order = Order.query.filter_by(id=id).first()
    if order is None:
         return make_response(jsonify({"message": 'bad request', "error": 'Order not found'}), 400)

    response = orderItems_schema.dump(order)
    return jsonify(response)  

if __name__ == '__main__':
    app.run(debug=True)