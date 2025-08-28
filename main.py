#Flask - gives us all the tools we need to run a flask app by creating an instance of this class
#jsonify - converst data to JSON
#request - allows us to interact with HTTP method requests as objects
from flask import Flask, jsonify, request

#SQLAlchemy - ORM to connect and relate python classes to SQL tables
from flask_sqlalchemy import SQLAlchemy

#DeclarativeBase - gives ust the base model functionallity to create the Classes as Model Classes for our db tables
#Mapped - Maps a Class attribute to a table column or relationship
#mapped_column - sets our Column and allows us to add any constraints we need (unique,nullable, primary_key)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

#Marshmallow - allows us to create a schema to valdite, serialize, and deserialize JSON data
from flask_marshmallow import Marshmallow

#date - use to create date type objects
from datetime import date

#List - is used to creat a relationship that will return a list of objects
from typing import List

#fields - lets us set a schema field which includes datatype and constraints
from marshmallow import ValidationError, fields

#select - acts as our SELECT FROM query
#delete - acts as our DELET query
from sqlalchemy import select, delete

# Connecting to DB-----------------------------------------------------------------------------------------------------------------------------------

app = Flask(__name__) # Creates an instance of our flask application.
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:Vikings58@localhost/ecommerce_api'

# Each class in our Model is going to inherit from the Base class, which ilmerits from the SQLAlchemy base model DeclarativeBase
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(app, model_class=Base)
ma = Marshmallow(app)

# User Table---------------------------------------------------------------------------------------------------------------------------------------------------------------------

class User(Base):
    __tablename__ = 'User' #Make your class name the same as your table name (trust me)
    #mapping class attributes to database table columns
    # name: datatype
    # mapped_column is how we add constraints
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(225), nullable=False)
    email: Mapped[str] = mapped_column(db.String(225))
    address: Mapped[str] = mapped_column(db.String(225))
    
    #This creates a one-to-many relationship to the Orders table.
    #This relates one Customer to many Orders.
    #back_populates ensures that the relationship is read on both ends. It creates a bidirectional relationship.
    #It ensures these two tables are in sync with one
    orders: Mapped[List["Orders"]] = db.relationship(back_populates='user') #back_populates ensures that both ends of the relationship have access to the other

# Association Table-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

# ASSOCIATION TABLE: order_products
# Because we have many-to-many relationships, an association table is required.
# This table facilitiates the relationship from one order to many products, or many products back to one order.
# This only includes foreign keys, so we don't need to create a complicated class model for it.


order_products = db.Table(
    "Order_Products",
    Base.metadata, #Allows this table to locate the foreign keys from the other Base class
    db.Column('order_id', db.ForeignKey('orders.id')),
    db.Column('product_id', db.ForeignKey('products.id'))
)

#Orders Table--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
class Orders(Base):

    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(primary_key=True)
    order_date: Mapped[date] = mapped_column(db.Date, nullable=False)

    # A foreign key constraint is a key used to link two tables together.
    # A foreign key is a field in one table that refers to the primary key in another table.
    # Here, we're specifying that the customer_id in an Order is the primary key for a Customer in the Customer table.
    user_id: Mapped[int] = mapped_column(db.ForeignKey('User.id'))

    #creating a many-to-one relationship to Customer table
    user: Mapped['User'] = db.relationship(back_populates='orders')  # property name is now 'user'

    #creating a many-to-many relationship to Products through or association table order_products
    #we specify that this relationship goes through a secondary table (order_products)
    products: Mapped[List[ 'Products' ]] = db.relationship(secondary=order_products, back_populates="orders")

#Products Table------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
class Products(Base):
    __tablename__= "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_name: Mapped[str] = mapped_column(db.String(255), nullable=False )
    price: Mapped[float] = mapped_column(db.Float, nullable=False)
    orders: Mapped[List['Orders']] = db.relationship(secondary=order_products, back_populates="products")


#Initialize DB and Create Tables-------------------------------------------------------------------------------------------
with app.app_context():
    db.create_all()


#Schemas---------------------------------------------------------------------------
# Define User Schema
class UserSchema(ma.SQLAlchemyAutoSchema): # SQLAlchemyAutoschemas create schema fields based on the SQLAlchemy model passed in.
    class Meta:
        model = User  # was 'Users', should be 'User'

class ProductSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Products

class OrderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Orders
        include_fk = True # Need this because Auto Schemas doesn't automatically recognize foreign keys (user_id)

user_schema = UserSchema()
users_schema = UserSchema(many=True)

product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)

# Routes--------------------------------------------------------------------------------------------------------------------

@app.route('/')
def home():
    return "Home"

# User Endpoints--------------------------------------------------------------------------------------------------------------

# Create a user with a POST request
@app.route("/users", methods=["POST"])
def add_user():
    try:
        user_data = user_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    new_user = User(name=user_data['name'], email=user_data['email'], address=user_data['address'])
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"Message": "New User added successfully!",
                    "user": user_schema.dump(new_user)}), 201


# Get all users with a GET method
@app.route("/users", methods=['GET'])
def get_customers():
    query = select(User)
    result = db.session.execute(query).scalars() #Execute query, and convert row objects into scalar objects (python useable)
    customers = result.all() #packs objects into a list
    return users_schema.jsonify(customers)


#Get specific user using a GET method and dynamic route
@app.route("/users/<int:id>", methods=['GET'])
def get_user(id):
    query = select(User).where(User.id == id)
    result = db.session.execute(query).scalars().first() # first() grabs the first object returned

    if result is None:
        return jsonify({"Error": "User not found"}), 404

    return user_schema.jsonify(result)

# Update a user by ID with PUT request
@app.route("/users/<int:id>", methods=["PUT"])
def update_user(id):
    user = db.session.get(User, id)
    if not user:
        return jsonify({"Error": "User not found"}), 404
    try:
        user_data = user_schema.load(request.json, partial=True)
    except ValidationError as e:
        return jsonify(e.messages), 400

    # Update fields if present in request
    if 'name' in user_data:
        user.name = user_data['name']
    if 'email' in user_data:
        user.email = user_data['email']
    if 'address' in user_data:
        user.address = user_data['address']

    db.session.commit()
    return jsonify({"Message": "User updated successfully!", "user": user_schema.dump(user)}), 200

# Delete a user by ID with DELETE request
@app.route("/users/<int:id>", methods=["DELETE"])
def delete_user(id):
    user = db.session.get(User, id)
    if not user:
        return jsonify({"Error": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"Message": "User deleted successfully!"}), 200



#Product Endpoints--------------------------------------------------------------------------------------------------------------------

# Create a product with a POST request
@app.route('/products', methods=['POST'])
def create_product():
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    new_product = Products(product_name=product_data['product_name'], price=product_data['price'])
    db.session.add(new_product)
    db.session.commit()

    return jsonify({"Messages": "New Product added!",
                    "product": product_schema.dump(new_product)}), 201

# Get all products with a GET request
@app.route("/products", methods=['GET'])
def get_products():
    query = select(Products)
    result = db.session. execute(query).scalars() #Exectute query, and convert row objects into scalar objects (python useable)
    products = result.all() #packs objects into a list
    return products_schema.jsonify(products)

# Get a specific product by ID with GET request
@app.route("/products/<int:id>", methods=["GET"])
def get_product(id):
    product = db.session.get(Products, id)
    if not product:
        return jsonify({"Error": "Product not found"}), 404
    return product_schema.jsonify(product)

# Update a product by ID with PUT request
@app.route("/products/<int:id>", methods=["PUT"])
def update_product(id):
    product = db.session.get(Products, id)
    if not product:
        return jsonify({"Error": "Product not found"}), 404

    try:
        product_data = product_schema.load(request.json, partial=True)
    except ValidationError as e:
        return jsonify(e.messages), 400

    # Update fields if present in request
    if 'product_name' in product_data:
        product.product_name = product_data['product_name']
    if 'price' in product_data:
        product.price = product_data['price']

    db.session.commit()
    return jsonify({"Message": "Product updated successfully!", "product": product_schema.dump(product)}), 200

# Delete a product by ID with DELETE request
@app.route("/products/<int:id>", methods=["DELETE"])
def delete_product(id):
    product = db.session.get(Products, id)
    if not product:
        return jsonify({"Error": "Product not found"}), 404

    db.session.delete(product)
    db.session.commit()
    return jsonify({"Message": "Product deleted successfully!"}), 200


#Order Endpoints---------------------------------------------------------------------------------------------------------------------

#Create an order using POST request
@app.route('/orders', methods=['POST'])
def add_order():
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    # Retrieve the user by its id.
    user = db.session.get(User, order_data['user_id'])

    # Check if the user exists.
    if user:
        new_order = Orders(order_date=order_data['order_date'], user_id = order_data['user_id'])

        db.session.add(new_order)
        db.session.commit()

        return jsonify({"Message": "New Order Placed!",
                        "order": order_schema.dump(new_order)}), 201
    else:
        return jsonify({"message": "Invalid customer id"}), 400

#Add item to order using PUT request
@app.route('/orders/<int:order_id>/add_product/<int:product_id>', methods=['PUT'])
def add_product(order_id, product_id):
    order = db.session.get(Orders, order_id) #can use .get when querying using Primary Key
    product = db.session.get(Products, product_id)

    if order and product: #check to see if both exist
        if product not in order.products: #Ensure the product is not already on the order
            order.products.append(product) #create relationship from order to product
            db.session.commit() #commit changes to db
            return jsonify({"Message": "Successfully added item to order."}), 200
        else:#Product is in order.products
            return jsonify({"Message": "Item is already included in this order."}), 400
    else:#order or product does not exist
        return jsonify({"Message": "Invalid order id or product id."}), 400
    
# Remove a product from an order using DELETE request
@app.route('/orders/<int:order_id>/remove_product/<int:product_id>', methods=['DELETE'])
def remove_product(order_id, product_id):
    order = db.session.get(Orders, order_id)
    product = db.session.get(Products, product_id)

    if order and product:
        if product in order.products:
            order.products.remove(product)
            db.session.commit()
            return jsonify({"Message": "Product removed from order."}), 200
        else:
            return jsonify({"Message": "Product not found in this order."}), 400
    else:
        return jsonify({"Message": "Invalid order id or product id."}), 400
    
# Get all orders for a user by user ID
@app.route("/orders/user/<int:user_id>", methods=["GET"])
def get_orders_for_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"Error": "User not found"}), 404

    orders = user.orders  # Access related orders via relationship
    return orders_schema.jsonify(orders)


# Get all products for an order by order ID
@app.route("/orders/<int:order_id>/products", methods=["GET"])
def get_products_for_order(order_id):
    order = db.session.get(Orders, order_id)
    if not order:
        return jsonify({"Error": "Order not found"}), 404

    products = order.products  # Access related products via relationship
    return products_schema.jsonify(products)







if __name__ == '__main__':
    app.run(debug=True)