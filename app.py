import datetime
import os
import uuid
from flask import Flask, make_response, render_template, request, redirect, session, url_for, flash
from pyrebase import pyrebase
import firebase_admin
from firebase_admin import storage 
from firebase_admin import credentials, auth, db
import secrets
from pyrebase import pyrebase
import requests
from werkzeug.utils import secure_filename

app = Flask(__name__)

firebaseConfig = {
    'apiKey': "AIzaSyDSSFnr9ILALdfnPjyjVsjwJlGhpWp-7f8",
    'databaseURL':'https://boletasmicreo-default-rtdb.firebaseio.com/',
    'authDomain': "boletasmicreo.firebaseapp.com",
    'projectId': "boletasmicreo",
    'storageBucket': "boletasmicreo.appspot.com",
    'messagingSenderId': "1028740254226",
    'appId': "1:1028740254226:web:5f0b3cea0c9547e981a6cb",
    'measurementId': "G-8Q67H7K1JY"
    }


cred = credentials.Certificate("C:/Users/patricio.toro/Desktop/bolatas_microgeo/static/json/boletasmicreo-firebase-adminsdk-qmus6-ddf535662a.json")



firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://boletasmicreo-default-rtdb.firebaseio.com/',
    'storageBucket': 'boletasmicreo.appspot.com'
})

ref = db.reference('usuario')


# Genera una clave secreta segura
secret_key = secrets.token_hex(16)  # Genera una cadena hexadecimal de 32 caracteres

# Asigna la clave secreta a tu aplicación Flask
app.secret_key = secret_key


# Create a Firebase Authentication instance
firebase = pyrebase.initialize_app(firebaseConfig)
db=firebase.database()
auth=firebase.auth()
storage = firebase.storage()


# Genera una clave secreta segura
secret_key = secrets.token_hex(16)  # Genera una cadena hexadecimal de 32 caracteres

# Asigna la clave secreta a tu aplicación Flask
app.secret_key = secret_key

#verificando autenticacion
def verificar_autenticacion():
    if 'user_id' in session:
        return True
    else:
        return False



# home
@app.route('/')
def home():
    if verificar_autenticacion():
        # El usuario está autenticado, obtén su ID de usuario
        user_id = session.get('user_id')

        # Accede a los datos del usuario desde la base de datos en tiempo real
        user_data = db.child("usuarios").child(user_id).get().val()

        if user_data:
            return render_template('home.html', user=user_data)
        else:
            # Si no se encuentran datos del usuario, redirige a la página de inicio de sesión
            return redirect(url_for('iniciosesion'))
    else:
        # Si el usuario no está autenticado, redirige a la página de inicio de sesión
        return redirect(url_for('iniciosesion'))



# inicio sesion
@app.route('/iniciosesion', methods=['GET', 'POST'])
def iniciosesion():
    if session:
        return redirect(url_for('home'))
    else:
        
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['contrasena']

            try:
                # Iniciar sesión con Firebase Authentication
                user = auth.sign_in_with_email_and_password(email, password)
                user_data = db.child("usuarios").child(user['localId']).get().val()
                

                if 'admin' in user_data and user_data['admin'] == True:
                    # Usuario es un administrador, almacenar en sesión
                    session['admin'] = True

                # Almacenar el ID del usuario en la sesión
                session['user_id'] = user['localId']
                session['idToken'] = user['idToken']
                # Almacenar el correo en la sesión
                session['user_email'] = email

                if 'admin' in user_data and user_data['admin'] == True:
                    # Usuario administrador, redirigir al panel de administrador
                    return redirect(url_for('admin_panel'))
                else:
                    # Usuario normal, redirigir a la página de inicio
                    return redirect(url_for('home'))

            except Exception as e:
                # Manejar errores, por ejemplo, si las credenciales son incorrectas
                error_message = "Credenciales incorrectas. Por favor, verifica tu correo y contraseña."
                return render_template('iniciosesion.html', error_message=error_message)

        # Retornar la página de inicio de sesión en caso de solicitud GET
        return render_template('iniciosesion.html')
    

# registro
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        email = request.form['email']
        password = request.form['contrasena']
        rut = request.form['rut']

        try:
            # Crear usuario en Firebase Authentication
            user = auth.create_user_with_email_and_password(email=email, password=password)

            # Datos del usuario a guardar en la base de datos
            user_data = {
                'nombre': nombre,
                'apellido': apellido,
                'email': email,
                'rut': rut    
            }

            # Guardar los datos del usuario en la base de datos
            db.child('usuarios').child(user['localId']).set(user_data)

            # Redirigir al usuario a la página de inicio de sesión
            return redirect(url_for('iniciosesion'))

        except Exception as e:
            error_message = str(e)
            return render_template('registro.html', error_message=error_message)

    # Retornar la página de registro en caso de solicitud GET
    return render_template('registro.html')


@app.route('/registrar_boleta', methods=['GET', 'POST'])
def registrar_boleta():
    if verificar_autenticacion():
        # El usuario está autenticado, obtén su ID de usuario
        user_id = session.get('user_id')

        # Accede a los datos del usuario desde la base de datos en tiempo real
        user_data = db.child("usuarios").child(user_id).get().val()

        if user_data:
            if request.method == 'POST':
                # Obtener los datos de la boleta del formulario
                nombre_boleta = request.form['nombre_boleta']
                # Obtener la imagen de la boleta del formulario
                imagen_boleta = request.files['imagen_boleta']

                try:
                    # Subir la imagen de la boleta a Firebase Storage
                    imagen_url = subir_imagen(imagen_boleta)

                    # Guardar los datos de la boleta y los datos del chofer en la base de datos
                    db.child('boletas').push({
                        'nombre_boleta': nombre_boleta,
                        'imagen_url': imagen_url,
                        'nombre_chofer': user_data['nombre'],
                        'rut_chofer': user_data['rut'],
                        'correo_chofer': user_data['email'],
                        'fecha_registro': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })

                    # Redireccionar a una página de éxito o a la página principal
                    return redirect(url_for('pagina_exito'))
                except Exception as e:
                    # Manejar errores
                    print("Error al registrar la boleta:", str(e))
                    flash("Error al registrar la boleta. Inténtalo de nuevo.", "error")
            
            # Si el método de la solicitud es GET, renderizar el formulario de registro de boleta
            return render_template('registrar_boleta.html', user=user_data)
        else:
            # Si no se encuentran datos del usuario, redirige a la página de inicio de sesión
            return redirect(url_for('iniciosesion'))
    else:
        # Si el usuario no está autenticado, redirige a la página de inicio de sesión
        return redirect(url_for('iniciosesion'))


def subir_imagen(imagen):
    if imagen:
        try:
            # Genera un nombre único para la imagen
            imagen_nombre = secure_filename
            carpeta_destino = "imagenes_boleta"

            # Especifica la ubicación del archivo en el almacenamiento
            imagen_ruta = f"{carpeta_destino}/{imagen_nombre}"

            # Sube la imagen al almacenamiento utilizando firebase_admin.storage
            blob = firebase_admin.storage.bucket().blob(imagen_ruta)
            blob.upload_from_string(imagen.read(), content_type=imagen.content_type)

            # Devuelve la URL de la imagen cargada
            imagen_url = blob.public_url
            return imagen_url
        except Exception as e:
            print("Error al subir la imagen al almacenamiento:", str(e))
    
    return None







# log out
@app.route('/logout')
def logout():
    try:
        # Cerrar la sesión de Firebase Authentication
        auth.current_user = None
        # Eliminar la sesión de Flask
        session.clear()
        return redirect(url_for('home'))
    except Exception as e:
        error_message = str(e)
        return render_template('error.html', error_message=error_message)

@app.route('/perfil_chofer')
def perfil_chofer():
    if verificar_autenticacion():
        # El usuario está autenticado, obtén su ID de usuario
        user_id = session.get('user_id')

        # Accede a los datos del usuario desde la base de datos en tiempo real
        user_data = db.child("usuarios").child(user_id).get().val()

        if user_data:
            return render_template('perfil_chofer.html', user=user_data)
        else:
            # Si no se encuentran datos del usuario, redirige a la página de inicio de sesión
            return redirect(url_for('iniciosesion'))
    else:
        # Si el usuario no está autenticado, redirige a la página de inicio de sesión
        return redirect(url_for('iniciosesion'))
    


            













if __name__ == '__main__':
    app.debug = True
    app.run()