import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF

class SistemaRegistroAsistencia:
    """
    Sistema de registro y gestión de asistencia.
    Este sistema permite registrar la asistencia de profesores a clases, generar reportes detallados
    por profesor y materia, y consultar estadísticas globales por carrera. Los datos se almacenan
    en una base de datos SQLite y se muestran en una interfaz Streamlit.
    """

    def __init__(self):
        """
        Inicializa el sistema de registro de asistencia y establece una conexión con la base de datos.
        Carga los datos de los profesores, materias, carreras y la relación profesor-materia.
        """
        self.conn = self.conectar_db()
        self.profesores, self.materias, self.carreras, self.profesor_materia = self.cargar_datos()

    def conectar_db(self):
        """
        Conecta a la base de datos SQLite 'FIME_v2.db'.
        
        Carga los datos de profesores, materias, carreras y la relación profesor-materia desde la base de datos.

        Returns:
            tuple: Contiene las listas de profesores, materias, carreras y un diccionario con la relación
                entre profesores y materias que imparten.
            sqlite3.Connection: Objeto de conexión a la base de datos.
        """
        return sqlite3.connect('FIME_v2.db')

    def cargar_datos(self):
        cursor = self.conn.cursor()

        # Cargar relaciones profesor-materia
        cursor.execute(""" 
            SELECT profesores.nombre, materias.nombre 
            FROM profesor_materia
            JOIN profesores ON profesor_materia.profesor_id = profesores.rowid
            JOIN materias ON profesor_materia.materia_id = materias.rowid
        """)
        profesor_materia = {row[0]: row[1] for row in cursor.fetchall()}

        # Cargar lista de profesores
        profesores = list(profesor_materia.keys())

        # Cargar lista de materias
        cursor.execute("SELECT nombre FROM materias")
        materias = [row[0] for row in cursor.fetchall()]

        # Cargar lista de carreras
        cursor.execute("SELECT nombre FROM carreras")
        carreras = [row[0] for row in cursor.fetchall()]

        return profesores, materias, carreras, profesor_materia

    def registrar_asistencia(self, nombre_profesor, *, materia, carrera=None, fecha=datetime.now(), asistio="Sí"):
        """
        Registra la asistencia de un profesor a una clase en la base de datos.

        Parameters:
            nombre_profesor (str): Nombre del profesor. 
            materia (str): Nombre de la materia que se está impartiendo.
            carrera (str, optional): Nombre de la carrera. Predeterminado es None.
            fecha (datetime, optional): Fecha de la clase. Predeterminado es la fecha actual.
            asistio (str, optional): Indica si el profesor asistió o no ("Sí" o "No").
        """
        # Si es "Otro maestro", omitir la validación
        if nombre_profesor != "Otro maestro":
            # Validar que el profesor exista
            if nombre_profesor not in self.profesores:
                st.error("El profesor ingresado no está registrado en el sistema.")
                return

            # Validar que el profesor imparte la materia seleccionada
            if self.profesor_materia.get(nombre_profesor) != materia:
                st.error(f"El profesor {nombre_profesor} no imparte la materia '{materia}'.")
                return

        # Registrar la asistencia si las validaciones pasan
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS asistencia (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            profesor TEXT,
                            materia TEXT,
                            carrera TEXT,
                            fecha TEXT,
                            asistio TEXT
                        )''')
        fecha_iso = fecha.isoformat()
        cursor.execute("INSERT INTO asistencia (profesor, materia, carrera, fecha, asistio) VALUES (?, ?, ?, ?, ?)", 
                    (nombre_profesor, materia, carrera, fecha_iso, asistio))
        self.conn.commit()
        st.success("¡Asistencia registrada exitosamente!")

    def eliminar_registros(self):
        """
        Elimina todos los registros de asistencia de la base de datos.
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM asistencia")
        self.conn.commit()

    def mostrar_reportes_detallados(self):
        """
        Muestra en la interfaz de usuario los reportes detallados de asistencia por profesor, 
        materia y estadísticas globales por carrera. Genera opciones interactivas para 
        seleccionar los criterios de reporte.
        """
        tab1, tab2, tab3 = st.tabs(["Reporte por Profesor", "Reporte por Materia", "Estadísticas Globales por Carrera"])

        # Reporte por Profesor
        with tab1:
            st.subheader("Reporte por Profesor")
            profesor_seleccionado = st.selectbox("Selecciona un Profesor", ["Otro maestro"] + self.profesores)

            fecha_inicio = st.date_input("Fecha de Inicio", value=datetime.now(), key="fecha_inicio_profesor")
            fecha_fin = st.date_input("Fecha de Fin", value=datetime.now(), key="fecha_fin_profesor")

            if st.button("Generar Reporte PDF por Profesor", key="boton_reporte_profesor_pdf"):
                cursor = self.conn.cursor()
                cursor.execute(""" 
                    SELECT carrera, profesor, materia, COUNT(*) as total_clases, 
                    SUM(CASE WHEN asistio = 'Sí' THEN 1 ELSE 0 END) as clases_impartidas, 
                    SUM(CASE WHEN asistio = 'No' THEN 1 ELSE 0 END) as clases_perdidas
                    FROM asistencia 
                    WHERE profesor = ? AND fecha BETWEEN ? AND ?
                    GROUP BY carrera, profesor, materia
                """, (profesor_seleccionado, fecha_inicio.isoformat(), fecha_fin.isoformat()))
                registros = cursor.fetchall()

                if registros:
                    # Generar PDF
                    self.generar_reporte_pdf(
                        registros, 
                        ["Carrera", "Profesor", "Materia", "Total Clases", "Clases Impartidas", "Clases Perdidas"],
                        fecha_inicio, fecha_fin,
                        "reporte_asistencia_profesor.pdf"
                    )
                else:
                    st.warning("No se encontraron registros para el profesor seleccionado en el rango de fechas.")

        # Reporte por Materia
        with tab2:
            st.subheader("Reporte por Materia")
            materia_seleccionada = st.selectbox("Selecciona una Materia", self.materias)
            fecha_inicio = st.date_input("Fecha de Inicio", value=datetime.now(), key="fecha_inicio_materia")
            fecha_fin = st.date_input("Fecha de Fin", value=datetime.now(), key="fecha_fin_materia")

            if st.button("Generar Reporte PDF por Materia", key="boton_reporte_materia_pdf"):
                cursor = self.conn.cursor()
                cursor.execute(""" 
                    SELECT carrera, profesor, materia, COUNT(*) as total_clases, 
                    SUM(CASE WHEN asistio = 'Sí' THEN 1 ELSE 0 END) as asistencias, 
                    SUM(CASE WHEN asistio = 'No' THEN 1 ELSE 0 END) as inasistencias
                    FROM asistencia 
                    WHERE materia = ? AND fecha BETWEEN ? AND ?
                    GROUP BY carrera, profesor, materia
                """, (materia_seleccionada, fecha_inicio.isoformat(), fecha_fin.isoformat()))
                registros = cursor.fetchall()

                if registros:
                    # Generar PDF
                    self.generar_reporte_pdf(
                        registros, 
                        ["Carrera", "Profesor", "Materia", "Total Clases", "Asistencias", "Inasistencias"],
                        fecha_inicio, fecha_fin,
                        "reporte_asistencia_materia.pdf"
                    )
                else:
                    st.warning("No se encontraron registros para la materia seleccionada en el rango de fechas.")

        # Estadísticas Globales por Carrera
        with tab3:
            st.subheader("Estadísticas Globales por Carrera")
            cursor = self.conn.cursor()
            cursor.execute(""" 
                SELECT carrera, COUNT(*) as total_clases, 
                ROUND(SUM(CASE WHEN asistio = 'Sí' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as tasa_cumplimiento
                FROM asistencia 
                GROUP BY carrera
            """)
            estadisticas = cursor.fetchall()
            st.table(pd.DataFrame(estadisticas, columns=['Carrera', 'Total Clases', 'Tasa de Cumplimiento (%)']))

            if st.button("Generar Reporte Global PDF por Carrera", key="boton_reporte_carrera_pdf"):
                if estadisticas:
                    # Generar PDF
                    self.generar_reporte_pdf(
                        estadisticas, 
                        ["Carrera", "Total Clases", "Tasa de Cumplimiento (%)"],
                        "N/A", "N/A",
                        "reporte_global_carrera.pdf"
                    )
                else:
                    st.warning("No hay datos de estadísticas para generar el reporte.")


    def generar_reporte_pdf(self, datos, columnas, fecha_inicio, fecha_fin, nombre_archivo):
        """
        Genera un archivo PDF a partir de los datos de un reporte.
        Parameters:
            datos (list of tuples): Datos a incluir en el reporte.
            columnas (list of str): Encabezados de las columnas en el reporte.
            fecha_inicio (datetime): Fecha de inicio del reporte.
            fecha_fin (datetime): Fecha de fin del reporte.
            nombre_archivo (str): Nombre del archivo PDF de salida.
        """
        pdf = FPDF(orientation="L")
        pdf.add_page()

        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, "Reporte de Asistencia", 0, 1, "C")

        pdf.set_font("Arial", "", 12)
        pdf.cell(200, 10, f"Fecha de Inicio: {fecha_inicio}   Fecha de Fin: {fecha_fin}", 0, 1, "C")
        pdf.ln(10)

        pdf.set_font("Arial", "B", 12)
        for columna in columnas:
            pdf.cell(60, 10, columna, 1, 0, "C")
        pdf.ln()

        pdf.set_font("Arial", "", 10)
        for fila in datos:
            for item in fila:
                pdf.cell(60, 10, str(item), 1, 0, "C")
            pdf.ln()

        pdf.output(nombre_archivo)
        st.success(f"Reporte generado: {nombre_archivo}")

    def cerrar_conexion(self):
        self.conn.close()

# Configuración de Streamlit y ejecución de funciones según la opción seleccionada en la interfaz
sistema = SistemaRegistroAsistencia()
st.set_page_config(page_title="Sistema de Registro de Asistencia", layout="wide")
st.markdown("<h1 style='text-align: center; color: #FF5733;'>Sistema de Registro de Clases</h1>", unsafe_allow_html=True)
st.sidebar.title("Navegación")
opcion = st.sidebar.selectbox("Selecciona una Opción", ["Registrar Asistencia", "Crear Reportes", "Info"])

if opcion == "Registrar Asistencia":
    st.header("Registrar Asistencia")
    profesor = st.selectbox("Profesor", ["Otro maestro"] + sistema.profesores)
    
    materia = st.selectbox("Selecciona la Materia", sistema.materias)
    carrera = st.selectbox("Carrera", sistema.carreras + ["No Aplica"])
    fecha = st.date_input("Fecha", value=datetime.now())
    asistio = st.radio("¿Asistió?", ["Sí", "No"])

    if st.button("Registrar"):
        sistema.registrar_asistencia(
            profesor,  # Usamos "Otro maestro" directamente si está seleccionado
            materia=materia, 
            carrera=(carrera if carrera != "No Aplica" else None), 
            fecha=fecha, 
            asistio=asistio
        )

elif opcion == "Crear Reportes":
    sistema.mostrar_reportes_detallados()

if opcion == "Info":
    st.markdown("<h1 style='text-align: center; color: #1E90FF;'>Sistema Automatizado de Registro de Asistencia de Profesores</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center;'>Integrantes:</h2>", unsafe_allow_html=True)
    integrantes = [
        "Luis Alejandro Mejía Durán",
        "Francisco Javier Águila Ceceña"
        "Carlos Isaac Tapia González",
        "Alejandro Rodríguez Meza",
        
    ]
    for integrante in integrantes:
        st.markdown(f"<h3 style='text-align: center;'>{integrante}</h3>", unsafe_allow_html=True)

    st.markdown("<h2 style='text-align: center;'>Descripción del Proyecto:</h2>", unsafe_allow_html=True)
    st.write("En este proyecto, se desarrollará un sistema automatizado que permita registrar si un profesor ha impartido una clase programada o no, "
            "con el propósito de llevar una estadística general de la asistencia de profesores por carrera. "
            "El jefe de grupo será responsable de registrar diariamente la información sobre si la clase fue impartida, "
            "especificando el profesor y la materia correspondiente.")

    st.markdown("<h3 style='text-align: center;'>Para más información, contactarse con nosotros directamente.</h3>", unsafe_allow_html=True)

    if st.button("Eliminar Todos los Registros"):
        sistema.eliminar_registros()
        st.success("Todos los registros han sido eliminados exitosamente.")
    else:
        st.write("¿Estás seguro de que deseas eliminar todos los registros? Esta acción no se puede deshacer.")
sistema.cerrar_conexion()
