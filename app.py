from datetime import datetime
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


cred = credentials.Certificate("static/json/boletasmicreo-firebase-adminsdk-qmus6-ddf535662a.json")



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


def is_admin():
    return 'admin' in session and session['admin'] == True


@app.route('/visualizarRegistro/<notaPedido>')
def visualizarRegistro(notaPedido):
    print(notaPedido)
    resultados = db.child("boletas").order_by_child("numero_orden").equal_to(notaPedido).get().val()
    print(resultados)
    return render_template('visualizarRegistro.html', resultados=resultados)


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

                # Almacenar el ID del usuario en la sesión
                session['user_id'] = user['localId']
                session['idToken'] = user['idToken']
                # Almacenar el correo en la sesión
                session['user_email'] = email

                if 'admin' in user_data and user_data['admin'] == True:
                    # Usuario es un administrador, almacenar en sesión
                    session['admin'] = True
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
    

@app.route('/admin_panel')
def admin_panel():
    if 'admin' in session and session['admin'] == True:
        # El usuario ha iniciado sesión como administrador

        try:
            # Obtener las boletas registradas desde la base de datos
            boletas = db.child('boletas').get().val()
            
            # Verificar si se obtuvieron datos de boletas
            if boletas:
                # Convertir el diccionario de boletas a una lista para iterar sobre ellas
                boletas_list = [boleta for boleta_id, boleta in boletas.items()]
            else:
                # Si no hay boletas registradas, inicializar la lista como vacía
                boletas_list = []

            return render_template('admin_panel.html', boletas_list=boletas_list)
        
        except Exception as e:
            # Manejar cualquier error que ocurra al recuperar las boletas
            flash("Error al obtener las boletas registradas: {}".format(str(e)), "error")
            return redirect(url_for('home'))
        
    else:
        flash("Acceso no autorizado", "error")
        return redirect(url_for('home'))


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
        # Obtener el ID del usuario de la sesión
        user_id = session.get('user_id')
        
        # Acceder a los datos del usuario desde la base de datos en tiempo real
        user_data = True

        if user_data:
            if request.method == 'POST':
                # Obtener los datos de la boleta del formulario
                fecha_entrega = request.form['fecha_entrega']
                numero_orden = request.form['numero_orden']
                codigo_seguimiento = request.form['codigo_seguimiento']
                nombre_transporte = request.form['nombre_transporte']
                patente_vehiculo = request.form['patente_vehiculo']
                #nombre_chofer = request.form['nombre_chofer']
                imagen_boleta = request.files['imagen_boleta']
                try:
                    # Verificar si el número de orden ya existe
                    orden_existente = db.child('boletas').order_by_child('numero_orden').equal_to(numero_orden).get().val()
                    if orden_existente:
                        raise Exception("El número de orden ya está en uso")

                    # Verificar si el número de seguimiento ya existe
                    seguimiento_existente = db.child('boletas').order_by_child('codigo_seguimiento').equal_to(codigo_seguimiento).get().val()
                    if seguimiento_existente:
                        raise Exception("El número de seguimiento ya está en uso")

                    # Subir la imagen de la boleta a Firebase Storage
                    imagen_url = subir_imagen(imagen_boleta)

                    # Guardar los datos de la boleta y los datos del chofer en la base de datos
                    db.child('boletas').push({
                        'fecha_entrega': fecha_entrega,
                        'numero_orden': numero_orden,
                        'codigo_seguimiento': codigo_seguimiento,
                        'nombre_transporte': nombre_transporte,
                        'patente_vehiculo': patente_vehiculo,
                        #'nombre_chofer': nombre_chofer,
                        'imagen_url': imagen_url,
                        #'fecha_registro': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })

                    # Redireccionar a una página de éxito o a la página principal
                    return redirect(url_for('home'))
                except Exception as e:
                    # Manejar errores
                    print("Error al registrar la boleta:", str(e))
                    flash("Error al registrar la boleta. Inténtalo de nuevo.", "error")

                                
            transportes = db.child('transportes').get().val()
            lista_nombres_transporte = []
            for key, value in transportes.items():
                lista_nombres_transporte.append(value['nombreTransporte'])
            # Si el método de la solicitud es GET, renderizar el formulario de registro de boleta
            return render_template('registrar_boleta.html', user=user_data, transportes=sorted(lista_nombres_transporte))
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
            imagen_nombre = secure_filename(imagen.filename)  # Corrección aquí
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
            # Obtener el RUT del chofer
            rut_chofer = user_data.get('rut')

            # Consultar las boletas asociadas al RUT del chofer
            boletas_ref = db.child('boletas').order_by_child('rut_chofer').equal_to(rut_chofer).get()
            boletas = boletas_ref.val() if boletas_ref else {}

            return render_template('perfil_chofer.html', user=user_data, boletas=boletas)
        else:
            # Si no se encuentran datos del usuario, redirige a la página de inicio de sesión
            return redirect(url_for('iniciosesion'))
    else:
        # Si el usuario no está autenticado, redirige a la página de inicio de sesión
        return redirect(url_for('iniciosesion'))
    

@app.route('/editar_boleta/<boleta_id>', methods=['GET', 'POST'])
def editar_boleta(boleta_id):
    # Verificar si el usuario está autenticado
    if 'user_id' in session:
        if request.method == 'POST':
            try:
                # Obtener los datos enviados por el formulario de edición
                nuevo_numero_orden = request.form['numero_orden']
                nuevo_numero_seguimiento = request.form['numero_seguimiento']
                nuevo_nombre_cliente = request.form['nombre_cliente']
                nueva_fecha_entrega = request.form['fecha_entrega']
                
                # Realizar la actualización en la base de datos
                db.child('boletas').child(boleta_id).update({
                    'numero_orden': nuevo_numero_orden,
                    'numero_seguimiento': nuevo_numero_seguimiento,
                    'nombre_cliente': nuevo_nombre_cliente,
                    'fecha_entrega': nueva_fecha_entrega
                })
                flash('Boleta actualizada correctamente', 'success')
                return redirect(url_for('perfil_chofer'))
            except Exception as e:
                flash('Error al actualizar la boleta: {}'.format(str(e)), 'error')
                return redirect(url_for('perfil_chofer'))
        
        # Si es una solicitud GET, mostrar el formulario de edición
        try:
            # Obtener los datos de la boleta a editar
            boleta = db.child('boletas').child(boleta_id).get().val()
            return render_template('editar_boleta.html', boleta=boleta)
        except Exception as e:
            flash('Error al obtener los datos de la boleta: {}'.format(str(e)), 'error')
            return redirect(url_for('perfil_chofer'))
    else:
        flash('Debe iniciar sesión para editar una boleta', 'error')
        return redirect(url_for('iniciosesion'))

def obtener_id_boleta(numero_orden):
    # Buscar todas las boletas con el mismo número de orden
    boletas = db.child("boletas").order_by_child("numero_orden").equal_to(numero_orden).get()
    boleta_ids = []
    for boleta in boletas.each():
        boleta_id = boleta.key()
        boleta_ids.append(boleta_id)
    return boleta_ids  # Devolver una lista de IDs de boletas encontradas

@app.route("/eliminar_boleta/<numero_orden>", methods=["POST"])
def eliminar_boleta(numero_orden):
    try:
        boleta_ids = obtener_id_boleta(numero_orden)
        if boleta_ids:      
            for boleta_id in boleta_ids:
                db.child("boletas").child(boleta_id).remove()
            print("Boleta(s) eliminada(s) correctamente")
        else:
            print("No se encontró ninguna boleta con ese número de orden")

        return redirect(url_for("admin_panel"))
    
    except Exception as e:
        print(f"Error al eliminar boleta: {e}")
        return redirect(url_for("admin_panel"))


def verificar_rut_chofer(rut_chofer, boleta_numero_orden):
    try:
        # Obtener la boleta desde la base de datos
        boleta = db.child('boletas').child(boleta_numero_orden).get().val()
        
        # Verificar si se encontró la boleta y si tiene un campo 'rut_chofer'
        if boleta and 'rut_chofer' in boleta:
            # Comparar el RUT del chofer en la boleta con el RUT proporcionado en la solicitud
            return boleta['rut_chofer'] == rut_chofer
        else:
            # Si la boleta no tiene un campo 'rut_chofer', devolver False
            return False
    except Exception as e:
        # Manejar cualquier error que ocurra durante la verificación del RUT del chofer
        print("Error al verificar el Rut del chofer:", str(e))
        return False

@app.route('/buscar_boletas', methods=['GET', 'POST'])
def buscar_boletas():
    if verificar_autenticacion():
        # Obtener la lista de choferes disponibles
        choferes = obtener_choferes()  # Función que obtiene la lista de choferes desde la base de datos

        if request.method == 'POST':
            # Obtener el nombre del chofer seleccionado en el formulario de búsqueda
            nombre_chofer = request.form['nombre_chofer']

            # Realizar una consulta a la base de datos para obtener las boletas del chofer seleccionado
            boletas_encontradas = obtener_boletas_por_chofer(nombre_chofer)
        else:
            # Si no se ha enviado un formulario, mostrar todas las boletas del primer chofer de la lista por defecto
            primer_chofer = choferes[0] if choferes else None
            boletas_encontradas = obtener_boletas_por_chofer(primer_chofer)

        # Renderizar la plantilla de resultados de búsqueda y pasar los choferes y las boletas encontradas
        return render_template('buscar_boletas.html', choferes=choferes, boletas_encontradas=boletas_encontradas)
    else:
        # Redirigir a la página de inicio de sesión si el usuario no está autenticado
        return redirect(url_for('iniciosesion'))

def obtener_boletas_por_chofer(nombre_chofer):
    # Realizar una consulta a la base de datos para buscar las boletas del chofer dado
    boletas_encontradas = []
    boletas = db.child('boletas').get().val()

    if boletas:
        for boleta_id, boleta in boletas.items():
            if boleta['nombre_chofer'] == nombre_chofer and not boleta.get('admin', False):
                boletas_encontradas.append(boleta)

    return boletas_encontradas

def obtener_choferes():
    # Obtener todos los usuarios de la base de datos
    usuarios = db.child('usuarios').get().val()

    # Inicializar una lista para almacenar los nombres de los choferes
    choferes = []

    # Verificar si existen usuarios y extraer los nombres de los choferes
    if usuarios:
        for uid, usuario in usuarios.items():
            if 'nombre' in usuario and not usuario.get('admin', False):
                choferes.append(usuario['nombre'])

    return choferes


@app.route('/restablecer_contrasena', methods=['GET', 'POST'])
def restablecer_contrasena():
    if verificar_autenticacion():
        # Si el usuario ya está autenticado, redirige a su perfil u otra página deseada
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        email = request.form['email']
        
        try:
            auth.send_password_reset_email(email)
            print("Se ha enviado un enlace de restablecimiento de contraseña a tu correo electrónico.", "success")
            return redirect(url_for('iniciosesion'))
        except Exception as e:
            print(f"Error al enviar el enlace de restablecimiento de contraseña: {str(e)}", "error")
    
    return render_template('restablecer_contrasena.html')


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')
