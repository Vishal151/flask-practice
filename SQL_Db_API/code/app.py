import os
from flask import Flask
from flask_restful import Api
from flask_jwt import JWT
from dotenv import load_dotenv

from security import authenticate, identity
from user import UserRegister
from item import Item, ItemList

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
api = Api(app)

jwt = JWT(app, authenticate, identity) # /auth

api.add_resource(Item, '/item/<string:name>')
api.add_resource(ItemList, '/items')
api.add_resource(UserRegister, '/register')

if __name__== '__main__':
    app.run(port=5000, debug=True)
    