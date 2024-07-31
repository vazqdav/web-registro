from flask import Flask, render_template, request, redirect, url_for, Response, make_response,send_from_directory, jsonify
from pymongo import MongoClient
from bson import ObjectId
import bcrypt
from io import BytesIO
from xhtml2pdf import pisa
from datetime import datetime
from werkzeug.utils import secure_filename
import os


app = Flask(__name__)

app.secret_key = "advpjsh"
client = MongoClient("mongodb+srv://davidnet:chetocheto@cluster0.0fkdavr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client['CAPTA']
collection = db['Paramedicos']
registros_collection = db['Registros']

# Ruta para mostrar todos los usuarios
@app.route('/Index')
def index():
    users = list(collection.find())
    return render_template('index.html', users=users)

# Ruta para agregar un nuevo usuario (Create)
@app.route('/new_user_modal', methods=['POST'])
def new_user_modal():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    user_type = request.form.get('user_type')
    address = request.form.get('address')
    phone = request.form.get('phone')
    
    # Hash de la contraseña usando bcrypt y convirtiendo a str
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    hashed_password_str = hashed_password.decode('utf-8')

    new_user = {
        "name": name,
        "email": email,
        "password": hashed_password_str,  # Almacenar el hash convertido a str
        "user_type": user_type,
        "address": address,
        "phone": phone
    }
    
    collection.insert_one(new_user)
    return redirect(url_for('index'))

# Ruta para eliminar un usuario por ID (Delete)
@app.route('/users/<user_id>/delete', methods=['POST'])
def delete_user(user_id):
    collection.delete_one({"_id": ObjectId(user_id)})
    return redirect(url_for('index'))

# Ruta para mostrar el formulario de edición de un usuario por ID (Read)
@app.route('/users/<user_id>/edit', methods=['GET'])
def edit_user_form(user_id):
    user = collection.find_one({"_id": ObjectId(user_id)})
    return render_template('edit_user.html', user=user)

# Ruta para actualizar un usuario por ID (Update)
@app.route('/users/<user_id>/edit', methods=['POST'])
def edit_user(user_id):
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    user_type = request.form.get('user_type')
    address = request.form.get('address')
    phone = request.form.get('phone')
    
    # Hash de la contraseña usando bcrypt si se proporciona una nueva contraseña
    if password:
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        hashed_password_str = hashed_password.decode('utf-8')
    else:
        # Si no se proporciona una nueva contraseña, mantener la existente
        current_user = collection.find_one({"_id": ObjectId(user_id)})
        hashed_password_str = current_user['password']

    updated_user = {
        "name": name,
        "email": email,
        "password": hashed_password_str,
        "user_type": user_type,
        "address": address,
        "phone": phone
    }
    
    collection.update_one({"_id": ObjectId(user_id)}, {"$set": updated_user})
    return redirect(url_for('index'))



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = collection.find_one({"email": email})

        if user:
            stored_hash = user['password'].encode('utf-8')  # Aseguramos que sea bytes
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                # Autenticación exitosa
                user_id = str(user['_id'])
                resp = make_response()
                resp.set_cookie('user_id', user_id)
                if user['user_type'] == 'Administrador':
                    resp.headers['Location'] = url_for('index')
                elif user['user_type'] == 'Paramedico':
                    resp.headers['Location'] = url_for('dashboard')
                return resp, 302
            else:
                error_message = 'Correo o contraseña incorrectos.'
                return render_template('login.html', error=error_message)

        error_message = 'Usuario no encontrado.'
        return render_template('login.html', error=error_message)

    return render_template('login.html')


@app.route('/perfil')
def perfil():
    user_id = request.cookies.get('user_id')
    if user_id:
        usuario = collection.find_one({"_id": ObjectId(user_id)})
        if usuario:
            return render_template('perfil.html', usuario=usuario)
    return redirect(url_for('login'))


@app.route('/perfiladmin')
def perfil_admin():
    user_id = request.cookies.get('user_id')
    if user_id:
        usuario = collection.find_one({"_id": ObjectId(user_id)})
        if usuario:
            return render_template('perfiladmin.html', usuario=usuario)
    return redirect(url_for('login'))


# Ruta para el dashboard
@app.route('/')
def inicio():
    return render_template('inicio.html')


# Ruta para el dashboard
@app.route('/registros')
def registros():
    return render_template('Historial.html')


app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Límite de 16 MB

# Asegúrate de que la carpeta de uploads existe
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/guardar_registro', methods=['GET', 'POST'])
def guardar_registro():
    if request.method == 'POST':
        
         # Obtener el ID del usuario desde la cookie
        user_id = request.cookies.get('user_id')
        if not user_id:
            return redirect(url_for('login'))
        
        # Obtener la información del usuario
        user = collection.find_one({'_id': ObjectId(user_id)})
        if not user:
            return redirect(url_for('login'))

        # Recoger los datos del formulario
        paciente_data = {
            'estado': request.form.get("estado"),
            'delegacion': request.form.get("delegacion"),
            'fecha': request.form.get("fecha"),
            'dia_semana': request.form.get("dia_semana"),
            'nombre_paciente': request.form.get('nombre_paciente'),
            'nombre_afiliacion': request.form.get('nombre_afiliacion'),
            'genero': request.form.get('genero'),
            'edad': request.form.get('edad'),
            'meses': request.form.get('meses'),
            'domicilio': request.form.get('domicilio'),
            'colonia_comunidad': request.form.get('colonia_comunidad'),
            'numero_telefonico': request.form.get('numero_telefonico'),
            'ocupacion': request.form.get('ocupacion'),
            'derechohabiente': request.form.get('derechohabiente'),
            'compania_seguro': request.form.get('compania_seguro'),
            'agente_causal': request.form.get('agente_causal'),
            'especifique': request.form.get('especifique'),
            'lesiones_causadas_por': request.form.get('lesiones_causadas_por'),
            'accidentes_automovilisticos': request.form.get('accidentes_automovilisticos'),
            'sobre_colision': request.form.get('sobre_colision'),
            'contra_objeto': request.form.get('contra_objeto'),
            'impacto': request.form.get('impacto'),
            'hundimiento': request.form.get('hundimiento'),
            'parabrisas': request.form.get('parabrisas'),
            'volante': request.form.get('volante'),
            'bolsa_de_aire': request.form.get('bolsa_de_aire'),
            'cinturon_seguridad': request.form.get('cinturon_seguridad'),
            'gesta': request.form.get('gesta'),
            'cesarea': request.form.get('cesarea'),
            'para': request.form.get('para'),
            'aborto': request.form.get('aborto'),
            'semanas_gestacion': request.form.get('semanas_gestacion'),
            'motivo_atencion': request.form.get('motivo_atencion'),
            'otromotivo': request.form.get('otromotivo'),
            'hora_llamada': request.form.get('hora_llamada'),
            'hora_despacho': request.form.get('hora_despacho'),
            'hora_arribo': request.form.get('hora_arribo'),
            'hora_traslado': request.form.get('hora_traslado'),
            'hora_hospital': request.form.get('hora_hospital'),
            'hora_disponible': request.form.get('hora_disponible'),
            'motivo_ubicacion': request.form.get('motivo_ubicacion'),
            'calle': request.form.get('calle'),
            'entre': request.form.get('entre'),
            'colonia_comunidad': request.form.get('colonia_comunidad'),
            'alcaldia_municipio': request.form.get('alcaldia_municipio'),
            'lugar_ocurrencia': request.form.get('lugar_ocurrencia'),
            'especifica_otro_lugar': request.form.get('especifica_otro_lugar'),
            'numero_ambulancia': request.form.get('numero_ambulancia'),
            'operador': request.form.get('operador'),
            'prestador_servicios': request.form.get('prestador_servicios'),
            'asignacion': request.form.get('asignacion'),
            'signos_vitales': {
                'hora': request.form.getlist('hora'),
                'fr': request.form.getlist('fr'),
                'fc': request.form.getlist('fc'),
                'tas': request.form.getlist('tas'),
                'tad': request.form.getlist('tad'),
                'saq2': request.form.getlist('saq2'),
                'temp': request.form.getlist('temp'),
                'gluc': request.form.getlist('gluc'),
                'glasgow': request.form.getlist('glasgow'),
                'trauma_score': request.form.getlist('trauma_score'),
                'ekg': request.form.getlist('ekg'),
            },
            'interrogatorio': {
                'alergias': request.form.get('alergias'),
                'primer_respondiente': request.form.get('primer_respondiente'),
                'medicamentos': request.form.get('medicamentos'),
                'enfermedades_cirugias': request.form.get('enfermedades_cirugias'),
                'ultima_comida': request.form.get('ultima_comida'),
                'eventos_previos': request.form.get('eventos_previos'),
            },
            'condicion_paciente': {
                'lts_x_min': request.form.get('lts_x_min'),
                'hiperventilacion': request.form.get('hiperventilacion'),
                'hemitorax': request.form.get('hemitorax'),
                'linea_iv': request.form.get('linea_iv'),
                'cateter': request.form.get('cateter'),
                'sitio_aplicacion': request.form.get('sitio_aplicacion'),
            },
            'otros_datos': {
                'hora': request.form.getlist('hora'),
                'medicamento': request.form.getlist('medicamento'),
                'dosis': request.form.getlist('dosis'),
                'via_administracion': request.form.getlist('via_administracion'),
                'terapia_electrica': request.form.getlist('terapia_electrica'),
                'tipo_soluciones': request.form.get('tipo_soluciones'),
                'especifique': request.form.get('especifique'),
                'tipo_rcp': request.form.get('tipo_rcp'),
            },
            'zonas_lesion': request.form.getlist('lesion_zones'),  # Checkboxes originales
            'niveles_deformidad': request.form.getlist('deformity_levels'),
            'nivel_conciencia': request.form.getlist('deformity_levels'),
            'via_aerea': request.form.getlist('via_aerea'),
            'reflejo_deglusion': request.form.getlist('reflejo_deglusion'),
            'observacion': request.form.getlist('observacion'),
            'auscultacion': request.form.getlist('auscultacion'),
            'presencia_pulsos': request.form.getlist('presencia_pulsos'), 
            'piel': request.form.getlist('piel'), 
            'caracteristicas': request.form.getlist('caracteristicas'),
            'condicion': request.form.getlist('condicion'),
            'estabilidad': request.form.getlist('estabilidad'),
            'Prioridad': request.form.getlist('Prioridad'), 
            'prioridad_secundaria': request.form.getlist('prioridad_secundaria'), # Nuevos checkboxes
            'usuario_nombre': user.get('name') 
        }
        
        # Manejo de las imágenes
        files = request.files.getlist('imagenes')  # Obtener todos los archivos subidos
        saved_files = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                saved_files.append(filename)  # Guardar solo el nombre del archivo en la lista
            else:
                return "Tipo de archivo no permitido", 400
        
        # Añadir la lista de archivos guardados al diccionario de datos del paciente
        paciente_data['imagenes'] = saved_files
        
        # Insertar datos en la colección 'Registros'
        registros_collection.insert_one(paciente_data)

        return redirect(url_for('mostrar_registros'))

    return render_template('crearregistro.html')




@app.route('/editar_registro/<registro_id>', methods=['GET', 'POST'])
def editar_registro(registro_id):
    if request.method == 'POST':
        datos = {
            "estado": request.form.get('estado', ''),
            "delegacion": request.form.get('delegacion', ''),
            "fecha": request.form.get('fecha', ''),
            "dia_semana": request.form.get('dia_semana', ''),
            "nombre_paciente": request.form.get('nombre_paciente', ''),
            "nombre_afiliacion": request.form.get('nombre_afiliacion', ''),
            "genero": request.form.get('genero', ''),
            "edad": request.form.get('edad', ''),
            "meses": request.form.get('meses', ''),
            "paramedico": request.form.get('paramedico', ''),
            "domicilio": request.form.get('domicilio', ''),
            "colonia_comunidad": request.form.get('colonia_comunidad', ''),
            "numero_telefonico": request.form.get('numero_telefonico', ''),
            "ocupacion": request.form.get('ocupacion', ''),
            "derechohabiente": request.form.get('derechohabiente', ''),
            "compania_seguro": request.form.get('compania_seguro', ''),
            "agente_causal": request.form.get('agente_causal', ''),
            "especifique": request.form.get('especifique', ''),
            "lesiones_causadas_por": request.form.get('lesiones_causadas_por', ''),
            "accidentes_automovilisticos": request.form.get('accidentes_automovilisticos', ''),
            "sobre_colision": request.form.get('sobre_colision', ''),
            "contra_objeto": request.form.get('contra_objeto', ''),
            "impacto": request.form.get('impacto', ''),
            "hundimiento": request.form.get('hundimiento', ''),
            "parabrisas": request.form.get('parabrisas', ''),
            "volante": request.form.get('volante', ''),
            "bolsa_de_aire": request.form.get('bolsa_de_aire', ''),
            "cinturon_seguridad": request.form.get('cinturon_seguridad', ''),
            "gesta": request.form.get('gesta', ''),
            "cesarea": request.form.get('cesarea', ''),
            "para": request.form.get('para', ''),
            "aborto": request.form.get('aborto', ''),
            "semanas_gestacion": request.form.get('semanas_gestacion', ''),
            "motivo_atencion": request.form.get('motivo_atencion', ''),
            "otromotivo": request.form.get('otromotivo', ''),
            "hora_llamada": request.form.get('hora_llamada', ''),
            "hora_despacho": request.form.get('hora_despacho', ''),
            "hora_arribo": request.form.get('hora_arribo', ''),
            "hora_traslado": request.form.get('hora_traslado', ''),
            "hora_hospital": request.form.get('hora_hospital', ''),
            "hora_disponible": request.form.get('hora_disponible', ''),
            "motivo_ubicacion": request.form.get('motivo_ubicacion', ''),
            "calle": request.form.get('calle', ''),
            "entre": request.form.get('entre', ''),
            "colonia_comunidad": request.form.get('colonia_comunidad', ''),
            "alcaldia_municipio": request.form.get('alcaldia_municipio', ''),
            "lugar_ocurrencia": request.form.get('lugar_ocurrencia', ''),
                        'especifica_otro_lugar': request.form.get('especifica_otro_lugar'),
            'numero_ambulancia': request.form.get('numero_ambulancia'),
            'operador': request.form.get('operador'),
            'prestador_servicios': request.form.get('prestador_servicios'),
            'asignacion': request.form.get('asignacion'),
            'signos_vitales': {
                'hora': request.form.get('hora'),
                'fr': request.form.get('fr'),
                'fc': request.form.get('fc'),
                'tas': request.form.get('tas'),
                'tad': request.form.get('tad'),
                'saq2': request.form.get('saq2'),
                'temp': request.form.get('temp'),
                'gluc': request.form.get('gluc'),
                'glasgow': request.form.get('glasgow'),
                'trauma_score': request.form.get('trauma_score'),
                'ekg': request.form.get('ekg'),
            },
            'interrogatorio': {
                'alergias': request.form.get('alergias'),
                'primer_respondiente': request.form.get('primer_respondiente'),
                'medicamentos': request.form.get('medicamentos'),
                'enfermedades_cirugias': request.form.get('enfermedades_cirugias'),
                'ultima_comida': request.form.get('ultima_comida'),
                'eventos_previos': request.form.get('eventos_previos'),
            },
            'condicion_paciente': {
                'lts_x_min': request.form.get('lts_x_min'),
                'hiperventilacion': request.form.get('hiperventilacion'),
                'hemitorax': request.form.get('hemitorax'),
                'linea_iv': request.form.get('linea_iv'),
                'cateter': request.form.get('cateter'),
                'sitio_aplicacion': request.form.get('sitio_aplicacion'),
            },
            'otros_datos': {
                'hora': request.form.get('hora'),
                'medicamento': request.form.get('medicamento'),
                'dosis': request.form.get('dosis'),
                'via_administracion': request.form.get('via_administracion'),
                'terapia_electrica': request.form.get('terapia_electrica'),
                'tipo_soluciones': request.form.get('tipo_soluciones'),
                'especifique': request.form.get('especifique'),
                'tipo_rcp': request.form.get('tipo_rcp'),
            },
            'zonas_lesion': request.form.get('lesion_zones'),
            'niveles_deformidad': request.form.get('deformity_levels'),
            'nivel_conciencia': request.form.getlist('deformity_levels'),
            'via_aerea': request.form.getlist('via_aerea'),
            'reflejo_deglusion': request.form.getlist('reflejo_deglusion'),
            'observacion': request.form.getlist('observacion'),
            'auscultacion': request.form.getlist('auscultacion'),
            'presencia_pulsos': request.form.getlist('presencia_pulsos'), 
            'piel': request.form.getlist('piel'), 
            'caracteristicas': request.form.getlist('caracteristicas'),
            'condicion': request.form.getlist('condicion'),
            'estabilidad': request.form.getlist('estabilidad'),
            'Prioridad': request.form.getlist('Prioridad'), 
            'prioridad_secundaria': request.form.getlist('prioridad_secundaria'), # Nuevos checkboxes
            
            
        }

        registros_collection.update_one({'_id': ObjectId(registro_id)}, {'$set': datos})

        return redirect(url_for('mostrar_registros'))

    registro = registros_collection.find_one({'_id': ObjectId(registro_id)})

    return render_template('editar_registro.html', registro=registro)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/mostrar_registros')
def mostrar_registros():
    user_id = request.cookies.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    user = collection.find_one({'_id': ObjectId(user_id)})
    if not user:
        return redirect(url_for('login'))

    page = int(request.args.get('page', 1))  # Obtener la página actual, por defecto es 1
    per_page = 9  # Número de registros por página
    skip = (page - 1) * per_page

    registros = list(registros_collection.find().skip(skip).limit(per_page))
    total_registros = registros_collection.count_documents({})
    total_pages = (total_registros + per_page - 1) // per_page  # Calcular el total de páginas

    return render_template('Registros.html', user=user, registros=registros, page=page, total_pages=total_pages)

@app.route('/graficos')
def graficos():
    return render_template('graficar.html')

@app.route('/data')
def get_data():
    # Obtener todos los documentos y extraer solo los campos necesarios
    data = list(registros_collection.find({}, {'_id': 0}))
    return jsonify(data)


@app.route('/historial', methods=['GET', 'POST'])
def historial():
    mes = request.form.get('mes')
    año = request.form.get('año')
    
    query = {}
    if mes and año:
        query['fecha'] = {'$regex': f'^{año}-{mes.zfill(2)}'}
    elif mes:
        query['fecha'] = {'$regex': f'-{mes.zfill(2)}-'}
    elif año:
        query['fecha'] = {'$regex': f'^{año}-'}
    
    registros = list(registros_collection.find(query))
    
    # Organizar registros por mes y año
    historial_por_mes = {}
    for registro in registros:
        fecha_str = registro.get('fecha')
        if fecha_str:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
            mes_año = fecha.strftime('%Y-%m')
            if mes_año not in historial_por_mes:
                historial_por_mes[mes_año] = []
            historial_por_mes[mes_año].append(registro)
    
    meses = [str(i).zfill(2) for i in range(1, 13)]
    años = [str(i) for i in range(2020, 2025)]
    
    return render_template('Historial.html', historial_por_mes=historial_por_mes, selected_mes=mes, selected_año=año, meses=meses, años=años)


@app.route('/dashboard')
def dashboard():
    # Obtener todos los registros de la colección 'Registros'
    datos = list(registros_collection.find())

    # Inicializar diccionarios para los datos de los gráficos
    motivo_atencion = {}
    lugar_ocurrencia = {}
    genero = {}
    agente_causal = {}

    for dato in datos:
        # Obtener datos con valores predeterminados en caso de que falten
        motivo = dato.get('motivo_atencion', 'Desconocido')
        lugar = dato.get('lugar_ocurrencia', 'Desconocido')
        gen = dato.get('genero', 'Desconocido')
        agente = dato.get('agente_causal', 'Desconocido')

        # Contar motivos de atención
        if motivo:
            if motivo in motivo_atencion:
                motivo_atencion[motivo] += 1
            else:
                motivo_atencion[motivo] = 1
        
        # Contar lugares de ocurrencia
        if lugar:
            if lugar in lugar_ocurrencia:
                lugar_ocurrencia[lugar] += 1
            else:
                lugar_ocurrencia[lugar] = 1
        
        # Contar géneros
        if gen:
            if gen in genero:
                genero[gen] += 1
            else:
                genero[gen] = 1
        
        # Agregar agentes causales directamente para el gráfico de anillos
        if agente:
            if agente in agente_causal:
                agente_causal[agente] += 1
            else:
                agente_causal[agente] = 1

    # Calcular el total de registros
    total_registros = len(datos)

    # Calcular accidentes graves y leves
    total_graves = sum(1 for dato in datos if 'critico' in dato.get('condicion', []))
    total_leves = sum(1 for dato in datos if 'no_critico' in dato.get('condicion', []))

    # Asegurarse de que todos los datos sean serializables
    motivo_atencion = motivo_atencion or {}
    lugar_ocurrencia = lugar_ocurrencia or {}
    genero = genero or {}
    agente_causal = agente_causal or {}

    # Enviar datos a la plantilla
    return render_template('dashboard.html', 
                           total_registros=total_registros, 
                           total_graves=total_graves, 
                           total_leves=total_leves, 
                           motivo_atencion=motivo_atencion,
                           lugar_ocurrencia=lugar_ocurrencia,
                           genero=genero,
                           agente_causal=agente_causal)



@app.route('/ver_mas/<registro_id>')
def ver_mas(registro_id):
    registro = registros_collection.find_one({'_id': ObjectId(registro_id)})
    if not registro:
        return redirect(url_for('mostrar_registros'))

    return render_template('vermas.html', registro=registro)

# Ruta para servir imágenes desde la carpeta uploads/images
@app.route('/imagesvermas/<filename>')
def image_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/eliminar_registro/<registro_id>', methods=['POST'])
def eliminar_registro(registro_id):
    registros_collection.delete_one({'_id': ObjectId(registro_id)})
    return redirect(url_for('mostrar_registros'))



@app.route('/generar_pdf/<registro_id>')
def generar_pdf(registro_id):
    registro = registros_collection.find_one({'_id': ObjectId(registro_id)})
    if not registro:
        return redirect(url_for('mostrar_registros'))

    # Renderizar la plantilla HTML
    html = render_template('imprimir.html', registro=registro)

    # Convertir HTML a PDF usando xhtml2pdf
    pdf = BytesIO()
    pisa.CreatePDF(BytesIO(html.encode('utf-8')), dest=pdf)

    # Obtener el contenido del buffer
    pdf.seek(0)
    response = make_response(pdf.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=registro.pdf'
    return response


@app.route('/buscar_usuario', methods=['POST'])
def buscar_usuario():
    search_query = request.json.get('search_query', '')
    if search_query:
        registros = list(registros_collection.find({"nombre_paciente": {"$regex": search_query, "$options": "i"}}))
    else:
        registros = list(registros_collection.find())
    
    # Serializar ObjectId y manejar la ruta de la imagen
    for registro in registros:
        registro['_id'] = str(registro['_id'])
        registro['imagenes'] = [url_for('uploaded_file', filename=imagen) for imagen in registro['imagenes']]
    
    return jsonify(registros)


@app.route('/images/<filename>')
def uploaded_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)






if __name__ == '__main__':
    app.run(debug=True)
