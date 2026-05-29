from app import app, bcrypt, create_all

with app.app_context():
    create_all(bcrypt)
