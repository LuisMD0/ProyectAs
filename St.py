import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF

class SistemaRegistroAsistencia:
    def __init__(self):
        self.conn = self.conectar_db()
        self.profesores, self.materias, self.carreras, self.profesor_materia = self.cargar_datos()

    def conectar_db(self):
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
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM asistencia")
        self.conn.commit()

    def generar_reporte_pdf(self, registros, columnas, fecha_inicio, fecha_fin, filename='reporte_asistencia.pdf'):
        pdf = FPDF(orientation="L")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(200, 10, 'Reporte de Asistencia', ln=True, align='C')
        
        # Añadir rango de fechas en el reporte
        pdf.set_font('Arial', 'I', 12)
        pdf.cell(200, 10, f"Periodo: {fecha_inicio} a {fecha_fin}", ln=True, align='C')
        pdf.ln(10)

        pdf.set_font('Arial', '', 12)

        if len(registros) > 0:
            for col in columnas:
                pdf.cell(50, 10, col, 1)
            pdf.ln()
            for registro in registros:
                for item in registro:
                    pdf.cell(50, 10, str(item), 1)
                pdf.ln()
        else:
            pdf.cell(200, 10, 'No se encontraron registros para el reporte.', ln=True, align='C')
        pdf.output(filename)
        st.success(f"Reporte generado exitosamente como '{filename}'")

    def mostrar_reportes_detallados(self):
        tab1, tab2, tab3 = st.tabs(["Reporte por Profesor", "Reporte por Materia", "Estadísticas Globales por Carrera"])

        with tab1:
            st.subheader("Reporte por Profesor")
            profesor_seleccionado = st.selectbox("Selecciona un Profesor", ["Selecciona...", "Otro maestro"] + self.profesores)
            
            fecha_inicio = st.date_input("Fecha de Inicio", value=datetime.now(), key="fecha_inicio_profesor")
            fecha_fin = st.date_input("Fecha de Fin", value=datetime.now(), key="fecha_fin_profesor")
            
            if st.button("Generar Reporte", key="boton_reporte_profesor"):
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
                    st.table(pd.DataFrame(registros, columns=["Carrera", "Profesor", "Materia", "Total Clases", "Clases Impartidas", "Clases Perdidas"]))
                    self.generar_reporte_pdf(registros, ["Carrera", "Profesor", "Materia", "Total Clases", "Clases Impartidas", "Clases Perdidas"], fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d'), f'reporte_asistencia_{profesor_seleccionado}.pdf')
                else:
                    st.warning("No se encontraron registros para el profesor seleccionado en el rango de fechas.")

        with tab2:
            st.subheader("Reporte por Materia")
            materia_seleccionada = st.selectbox("Selecciona una Materia", self.materias)
            fecha_inicio = st.date_input("Fecha de Inicio", value=datetime.now(), key="fecha_inicio_materia")
            fecha_fin = st.date_input("Fecha de Fin", value=datetime.now(), key="fecha_fin_materia")
            
            if st.button("Generar Reporte", key="boton_reporte_materia"):
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
                    st.table(pd.DataFrame(registros, columns=["Carrera", "Profesor", "Materia", "Total Clases", "Asistencias", "Inasistencias"]))
                    self.generar_reporte_pdf(registros, ["Carrera", "Profesor", "Materia", "Total Clases", "Asistencias", "Inasistencias"], fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d'), f'reporte_asistencia_{materia_seleccionada}.pdf')
                else:
                    st.warning("No se encontraron registros para la materia seleccionada en el rango de fechas.")

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

            if st.button("Generar Reporte Global por Carrera", key="boton_reporte_carrera"):
                if estadisticas:
                    self.generar_reporte_pdf(estadisticas, ["Carrera", "Total Clases", "Tasa de Cumplimiento (%)"], "N/A", "N/A", 'reporte_global_carrera.pdf')
                else:
                    st.warning("No hay datos de estadísticas para generar el reporte.")

    def cerrar_conexion(self):
        self.conn.close()

sistema = SistemaRegistroAsistencia()
st.set_page_config(page_title="Sistema de Registro de Asistencia", layout="wide")
st.markdown("<h1 style='text-align: center; color: #FF5733;'>Sistema de Registro de Clases</h1>", unsafe_allow_html=True)
st.sidebar.title("Navegación")
opcion = st.sidebar.selectbox("Selecciona una Opción", ["Registrar Asistencia", "Crear Reportes", "Info"])

if opcion == "Registrar Asistencia":
    st.sidebar.markdown("<h2 style='text-align: center; color: #33FFBD;'>Registrar Asistencia</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("<h3 style='text-align: center; color: #33FFBD;'>Selecciona Profesor</h3>", unsafe_allow_html=True)
        profesor = st.selectbox("Profesor", ["Otro maestro"] + sistema.profesores)
        if profesor == "Otro maestro":
            materia = st.selectbox("Selecciona la Materia", sistema.materias)
            
        else:
            materia=sistema.profesor_materia.get(profesor,"")
            st.text('Materia:')
            st.text(materia)
        carrera = st.selectbox("Carrera", sistema.carreras + ["No Aplica"])


    with col2:
        st.markdown("<h3 style='text-align: center; color: #33FFBD;'>Selecciona Fecha</h3>", unsafe_allow_html=True)
        fecha = st.date_input("Fecha", value=datetime.now())
        st.markdown("<h3 style='text-align: center; color: #33FFBD;'>¿Asistió?</h3>", unsafe_allow_html=True)
        asistio = st.radio("Selecciona", options=["Sí", "No"], horizontal=True)

    with col3:
        st.markdown("<h3 style='text-align: center; color: #33FFBD;'>Confirmar</h3>", unsafe_allow_html=True)
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
    st.markdown("<h2 style='text-align: center; color: #FF5733;'>Información del Sistema</h2>", unsafe_allow_html=True)
    st.write("Este sistema permite registrar la asistencia de los estudiantes y generar reportes detallados.")
    
    if st.button("Eliminar Todos los Registros"):
        sistema.eliminar_registros()
        st.success("Todos los registros han sido eliminados exitosamente.")

sistema.cerrar_conexion()
