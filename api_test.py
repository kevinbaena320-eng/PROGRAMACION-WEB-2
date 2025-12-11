from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import mercadopago
import random
from datetime import timedelta
import os

app = Flask(__name__)

# CORS CONFIG CORRECTO
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# MANEJO GLOBAL DE OPTIONS → SOLUCIONA EL ERROR 404 EN OPTIONS
@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        headers = response.headers
        headers['Access-Control-Allow-Origin'] = '*'
        headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        return response

sdk = mercadopago.SDK("TEST-4267539412609633-112610-ab8635bd81d4c4c8ff768d6d7d18a939-652880717")

DB_USER = 'root'
DB_PASSWORD = 'UPmwNiLcUKfDcUBUbpYiwulOlmIuNEai'
DB_HOST = 'crossover.proxy.rlwy.net:24110'
DB_NAME = 'poryecto'

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Cancion(db.Model):
    __tablename__ = 'canciones'
    
    id_cancion = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    id_album = db.Column(db.Integer, nullable= False)
    duracion = db.Column(db.String(250), nullable=False)
    url_imagen = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            'id_cancion': self.id_cancion,
            'titulo': self.titulo,
            'id_album': self.id_album,
            'duracion': self.duracion,
            'url_imagen': self.url_imagen
        }

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id_usuarios = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(100), unique=True, nullable=False)
    contraseña_hash = db.Column(db.String(255), nullable=False)
    fecha_registro = db.Column(db.DateTime)
    tipo_usuario = db.Column(db.String(50))
    
    def to_dict(self):
        return {
            'id_usuarios': self.id_usuarios,
            'nombre': self.nombre,
            'correo': self.correo,
            'tipo_usuario': self.tipo_usuario
        }

class TwoFACode(db.Model):
    __tablename__ = 'twofa_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    code = db.Column(db.String(6), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)


@app.route('/processpayment', methods=['POST', 'OPTIONS'])
def processPayment():
    parameters = request.get_json(silent=True)

    payment = parameters.get('formdata')
    iddevice = parameters.get('iddevice')

    if not payment.get('token'):
        return jsonify({"error": "Faltan datos obligatorios"}), 400

    amount = payment.get('transaction_amount')
    email = payment.get('payer').get('email')

    payment_data = {
        "transaction_amount": float(amount),
        "token": payment.get('token'),
        "payment_method_id": payment.get('payment_method_id'),
        "issuer_id": payment.get('issuer_id'),
        "description": "Descripcion del pago",
        "installments": 1,
        "statement_descriptor": "Description",
        "payer": {
            "first_name": "Jonathan",
            "last_name": "Guevara",
            "email": email,
        },
        "additional_info": {
            "items": [
                {
                    "title": "Producto",
                    "quantity": 1,
                    "unit_price": float(amount)
                }
            ]
        },
        "capture": True,
        "binary_mode": False
    }

    try:
        result = sdk.payment().create(payment_data)
        payment = result.get("response", {})
    except Exception as e:
        return jsonify({"mensaje": f"Error MercadoPago: {e}", "status": "error"}), 500

    if payment.get("status") == "approved":
        return jsonify({
            "mensaje": "Pago exitoso",
            "status": "success",
            'data': payment
        }), 200
    else:
        return jsonify({
            "mensaje": "Pago rechazado",
            "status": "error",
            'data': payment
        }), 400


@app.route('/site/register', methods=['POST', 'OPTIONS'])
def register():
    try:
        data = request.get_json()
        nombre = data.get('nombre')
        correo = data.get('correo')
        password_plano = data.get('password')
        tipo_usuario = data.get('tipo_usuario', 'usuario_regular')

        if not nombre or not correo or not password_plano:
            return jsonify({"mensaje": "Faltan datos", "status": "error"}), 400

        if Usuario.query.filter_by(correo=correo).first():
            return jsonify({"mensaje": "Correo ya registrado", "status": "error"}), 409

        hashed_password = generate_password_hash(password_plano)

        nuevo = Usuario(
            nombre=nombre,
            correo=correo,
            contraseña_hash=hashed_password,
            fecha_registro=datetime.now(),
            tipo_usuario=tipo_usuario
        )

        db.session.add(nuevo)
        db.session.commit()

        return jsonify({"mensaje": "Usuario registrado", "status": "success"}), 201

    except Exception as e:
        return jsonify({"mensaje": f"Error interno: {e}", "status": "error"}), 500


@app.route('/site/login', methods=['POST', 'OPTIONS'])
def login_step1():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"mensaje": "Faltan credenciales", "status": "error"}), 400

        user = Usuario.query.filter_by(correo=email).first()

        if not user or not check_password_hash(user.contraseña_hash, password):
            return jsonify({"mensaje": "Credenciales inválidas", "status": "error"}), 401

        code = str(random.randint(100000, 999999))
        expiration = datetime.now() + timedelta(minutes=5)

        record = TwoFACode(user_id=user.id_usuarios, code=code, expires_at=expiration)
        db.session.add(record)
        db.session.commit()

        print("\n====== CÓDIGO 2FA ======")
        print(f"Email: {email}")
        print(f"Code: {code}")
        print("========================\n")

        return jsonify({
            "mensaje": "Se requiere 2FA",
            "status": "2fa_required",
            "user_id": user.id_usuarios
        }), 200

    except Exception as e:
        return jsonify({"mensaje": f"Error interno: {e}", "status": "error"}), 500


@app.route('/site/verify_2fa', methods=['POST', 'OPTIONS'])
def verify_2fa():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        code = data.get('code')

        record = TwoFACode.query.filter_by(user_id=user_id, code=code).first()

        if not record:
            return jsonify({"mensaje": "Código incorrecto", "status": "error"}), 401

        if datetime.now() > record.expires_at:
            return jsonify({"mensaje": "Código expirado", "status": "error"}), 401

        user = Usuario.query.get(user_id)
        token = f"jwt_{user.tipo_usuario}_{user.nombre}"

        db.session.delete(record)
        db.session.commit()

        return jsonify({
            "mensaje": "Login exitoso",
            "status": "success",
            "token": token,
            "user": user.to_dict()
        }), 200

    except Exception as e:
        return jsonify({"mensaje": f"Error interno: {e}", "status": "error"}), 500


@app.route('/store/products/<int:producto_id>', methods=["GET", "OPTIONS"])
def getProducto(producto_id):
    try:
        producto = Cancion.query.get(producto_id)

        if producto is None:
            return jsonify({"mensaje": "Canción no encontrada", "status": "error"}), 404

        return jsonify({
            "mensaje": "Producto encontrado",
            "status": "success",
            "data": producto.to_dict()
        }), 200

    except Exception as e:
        return jsonify({"mensaje": f"Error interno: {e}", "status": "error"}), 500


@app.route('/store/products', methods=['GET', 'OPTIONS'])
def getProducts():
    try:
        canciones = Cancion.query.all()
        return jsonify({
            "mensaje": "Productos obtenidos",
            "status": "success",
            "data": [c.to_dict() for c in canciones]
        }), 200
    except Exception as e:
        return jsonify({"mensaje": f"Error BD: {e}", "status": "error"}), 500


if __name__ == '__main__':
    app.run(debug=True, threaded=True)

