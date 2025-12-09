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
CORS(app)
sdk = mercadopago.SDK("TEST-4267539412609633-112610-ab8635bd81d4c4c8ff768d6d7d18a939-652880717")

DB_USER = 'root'
DB_PASSWORD = 'UPmwNiLcUKfDcUBUbpYiwulOlmIuNEai'
DB_HOST = '@crossover.proxy.rlwy.net'
DB_NAME = 'poryecto'

#app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}'
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#app.config['MAIL_SERVER'] = 'smtp.gmail.com'
#app.config['MAIL_PORT'] = 465
#app.config['MAIL_USE_TLS'] = True
#app.config['MAIL_USE_SSL'] = False
#app.config['MAIL_USERNAME'] = 'kevinbaena320@gmail.com'
#app.config['MAIL_PASSWORD'] = 'mbaw xnsp faec kwfy'  # usa contraseña de app (Gmail)


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


@app.route('/processpayment', methods=['POST'])
def processPayment():
    parameters = request.get_json(silent=True)

    payment = parameters.get('formdata')
    idcarrito = parameters.get('idfoliocarrito')
    iddevice = parameters.get('iddevice')

    if not payment.get('token'):
        return jsonify({"error": "Faltan datos obligatorios"}), 400

    # PROCESAR LA COMPRA Y REGISTRAR O MODIFICAR LA BASE DE DATO
    # DE ACUERDO A LA LOGICA DE NEGOCIO

    amount = payment.get('transaction_amount')
    email = payment.get('payer').get('email')

    payment_data = {
        "transaction_amount": float(amount),
        "token": payment.get('token'),
        "payment_method_id" : payment.get('payment_method_id'),
        "issuer_id" : payment.get('issuer_id'),
        "description": "Descripcion del pago a Realizar",
        "installments": 1, # pago en una sola exhibición
        "statement_descriptor" : 'Description',
        "payer": {
        "first_name" : 'Jonathan',
        "last_name": "Guevara",
        "email": email,
    },
    "additional_info": {
    "items": [
    {
    "title": "Nombre del Producto",
    "quantity": 1,
    "unit_price": float(amount)
    }
    ]
    },
    "capture" : True,
    "binary_mode": False, # evita pagos pendientes: solo aprueba o rechaza
    # "device_id": iddevice
    }


    request_options = RequestOptions()
    import uuid
    UUID = str(uuid.uuid4())

    request_options.custom_headers = {
    "X-Idempotency-Key": UUID,
    "X-meli-session-id": iddevice
    }

    result = sdk.payment().create(payment_data, request_options)
    payment = result.get("response", {})

    if( payment.get("status") == 'approved' and payment.get('status_detail') == 'accredited' ):
    # PROCESAR SUS DATOS EN LA BD O LO QUE TENGAN QUE HACER
    # DAR RESPUESTA
        respuesta = {
            "mensaje" : "Mensaje de Exito",
            "status" : "success",
            'data': payment
    }

        return jsonify(respuesta), 200
    else:

        respuesta = {
            "mensaje" : "Mensaje de Error",
            "status" : "error",
            'data': payment
    }

    return jsonify(respuesta), 400

@app.route("/preferencemp", methods=["GET"])
def crear_preferecia():

    preference_data = {
        "items": [
            {
            "tittle" : "Nombre del Producto",
            "quantity" : 1,
            "unit_price" : 100.00
            }
        ],

        "back_urls": {
            "success": "https://carpinteriareyna.com/success",
            "failure": "https://carpinteriareyna.com/failure",
            "pending": "https://carpinteriareyna.com/pending",            
        },
       #"auto_return": "approved",
    }
    #crear preferecia
    preference_response = sdk.preference().create(preference_data)
    preference = preference_response["response"]

    data = {
        "id": preference["id"],
        "init_point": preference["init_point"],
        "sandbox_init_point": preference["sandbox_init_point"] 

    }
    respuesta = {
        "mensaje": "Mensaje de exito",
        "status": "success",
        'data': data
    }
    return jsonify(respuesta), 200

@app.route('/site/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        nombre = data.get('nombre')
        correo = data.get('correo')
        password_plano = data.get('password') 
        
        tipo_usuario = data.get('tipo_usuario', 'usuario_regular') 

        if not nombre or not correo or not password_plano:
            return jsonify({
                "mensaje": "Faltan datos requeridos (nombre, correo o password)",
                "status": "error"
            }), 400

        if Usuario.query.filter_by(correo=correo).first():
            return jsonify({
                "mensaje": f"El correo '{correo}' ya está registrado.",
                "status": "error"
            }), 409 

        hashed_password = generate_password_hash(password_plano)
        
        new_user = Usuario(
            nombre=nombre,
            correo=correo,
            contraseña_hash=hashed_password, 
            fecha_registro=datetime.now(), 
            tipo_usuario=tipo_usuario
        )

        db.session.add(new_user)
        db.session.commit()
        db.session.refresh(new_user)

        return jsonify({
            "mensaje": f"Usuario {new_user.nombre} registrado exitosamente.",
            "status": "success",
        }), 201 

    except Exception as e:
        db.session.rollback() 
        print(f"ERROR PYMYSQL AL REGISTRAR: {e}")
        return jsonify({
            "mensaje": f"Error interno al registrar usuario: {e}",
            "status": "error"
        }), 500

@app.route('/site/login', methods=['POST'])
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

        # ---------- GENERAR CÓDIGO ----------
        code = str(random.randint(100000, 999999))
        expiration = datetime.now() + timedelta(minutes=5)

        # GUARDAR EN LA BD
        twofa_record = TwoFACode(user_id=user.id_usuarios, code=code, expires_at=expiration)
        db.session.add(twofa_record)
        db.session.commit()

        # 🔥 MOSTRAR EL CÓDIGO EN CONSOLA
        print("\n==============================")
        print(f"💡 CÓDIGO 2FA PARA {email}: {code}")
        print("==============================\n")

        return jsonify({
            "mensaje": "Se requiere verificación 2FA",
            "status": "2fa_required",
            "user_id": user.id_usuarios,
            "debug_code": code  # <-- Puedes quitar esto si deseas
        }), 200

    except Exception as e:
        return jsonify({"mensaje": f"Error interno: {e}", "status": "error"}), 500

@app.route('/site/verify_2fa', methods=['POST'])
def verify_2fa():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        code = data.get('code')

        if not user_id or not code:
            return jsonify({"mensaje": "Datos incompletos", "status": "error"}), 400

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
            "mensaje": "Autenticación exitosa",
            "status": "success",
            "token": token,
            "user_info": user.to_dict()
        }), 200

    except Exception as e:
        return jsonify({"mensaje": f"Error interno: {e}", "status": "error"}), 500


@app.route('/store/products/<int:producto_id>', methods=["GET"])
def getProducto(producto_id):
    try:
        producto = Cancion.query.get(producto_id)   # ← CORREGIDO AQUÍ

        if producto is None:
            return jsonify({
                "mensaje": f"Cancion con ID {producto_id} no encontrada",
                "status": "error",
                "data": None
            }), 404

        respuesta = {
            "mensaje": f"Detalle de la cancion ID {producto_id} obtenido con exito",
            "status" : "success",
            "data" : producto.to_dict()
        }

        return jsonify(respuesta), 200

    except Exception as e:
        return jsonify({
            "mensaje": f"Error al obtener el producto: {e}",
            "status": "error",
            "data": None
        }), 500
    except Exception as e:
            return jsonify({
                "mensaje": f"Error al obtener el producto: {e}",
                "status": "error",
                "data": None
            }),500

@app.route('/store/products', methods=['GET'])
def getProducts():

    try: 
        canciones_db = Cancion.query.all()
        canciones_json = [cancion.to_dict() for cancion in canciones_db]

        respuesta = {
            "mensaje": f"Lista de {len(canciones_json)} cancion obtenida de poryecto",
            "status" : "success",
            "data" : canciones_json
        }
        return jsonify(respuesta),200
    except Exception as e:
        return jsonify({
            "mensaje": f"Error al obtener productos de la BD: {e}",
            "status": "error",
            "data": []
        }), 500

    
    respuesta = {
        "mensaje": "Mensaje de Exito",
        "status": "success",
        "data": data
    }

    return jsonify(respuesta)

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
