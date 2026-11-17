
# ============================================================
# PROYECTO ACTUARIAL
# COTIZADOR DE SEGUROS DE VIDA - MVP
# ============================================================

import streamlit as st
import pandas as pd
from datetime import date
from io import BytesIO

# ============================================================
# 1. CONFIGURACION
# ============================================================

st.set_page_config(
    page_title="Calculo de primas de seguros de Vida",
    layout="wide"
)

st.title("Calculo de primas de seguros de Vida")
st.caption("Cotizador actuarial ")

st.divider()


# ============================================================
# 2. FUNCIONES ACTUARIALES AUXILIARES
# ============================================================

def cumpleanos_en_anio(fecha_nacimiento, anio):

    try:
        return fecha_nacimiento.replace(year=anio)

    except ValueError:
        # Tratamiento de nacimientos el 29 de febrero
        return date(anio, 2, 28)


def calcular_edad_actuarial(fecha_nacimiento, fecha_efecto):

    edad = fecha_efecto.year - fecha_nacimiento.year

    ultimo_cumpleanos = cumpleanos_en_anio(
        fecha_nacimiento,
        fecha_efecto.year
    )

    if ultimo_cumpleanos > fecha_efecto:
        edad -= 1

    siguiente_cumpleanos = cumpleanos_en_anio(
        fecha_nacimiento,
        fecha_efecto.year + 1
    )

    dias_desde = (fecha_efecto - ultimo_cumpleanos).days
    dias_hasta = (siguiente_cumpleanos - fecha_efecto).days

    # Redondeo al cumpleaños más próximo
    # En caso de empate se conserva la edad cumplida

    if dias_hasta < dias_desde:
        edad += 1

    return edad


def sumar_anios(fecha, anios):

    try:
        return fecha.replace(year=fecha.year + anios)

    except ValueError:
        return date(fecha.year + anios, 2, 28)


# ============================================================
# 3. ALMACENAMIENTO DE SOLICITUDES
# ============================================================

columnas = [
    "producto",
    "fecha_nacimiento",
    "edad_actuarial",
    "fecha_efecto",
    "duracion",
    "edad_cobertura",
    "capital_asegurado",
    "modalidad_pago",
    "tipo_de_pago"
]

if "polizas" not in st.session_state:
    st.session_state.polizas = pd.DataFrame(columns=columnas)



# ============================================================
# 4. FORMULARIO DE COTIZACION
# ============================================================

st.header("Nueva tarificacion")

with st.form("formulario"):

    # --------------------------------------------------------
    # BLOQUE A: DATOS DEL ASEGURADO
    # --------------------------------------------------------

    st.subheader("01. Datos del asegurado")

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        fecha_nacimiento = st.date_input(
            "Fecha de nacimiento",
            value=date(1990, 1, 1),
            min_value=date(1900, 1, 1),
            max_value=date.today(),
            format="DD/MM/YYYY"
        )

    with col2:

        fecha_efecto = st.date_input(
            "Fecha de efecto",
            value=date.today(),
            min_value=date.today(),
            format="DD/MM/YYYY"
        )

    with col3:

        producto = st.selectbox(
            "Producto",
            ["Vida Entera"]
        )
        
    with col4:

        tipo_de_pago = st.selectbox(
            "Tipo de Pago",
            ["Prepagable", "Postpagable"]
        )

 
    # --------------------------------------------------------
    # BLOQUE B: CARACTERISTICAS DEL SEGURO
    # --------------------------------------------------------
    
    st.divider()
    
    st.subheader("02. Características del seguro")
    
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
    
        capital_asegurado = st.number_input(
            "Capital asegurado (€)",
            min_value=1000.0,
            max_value=10000000.0,
            value=100000.0,
            step=5000.0,
            format="%.2f"
        )
    
    with col6:
    
        duracion = st.selectbox(
            "Duración del seguro (años)",
            list(range(1, 41)),
            index=19
        )
    
    with col7:
    
        edad_cobertura = st.number_input(
            "Edad Cobertura",
            min_value=18,
            max_value=100,
            value=60,
            step=1,
            format="%d"
        )
    
    with col8:
        
            modalidad_pago = st.selectbox(
                "Modalidad de pago",
                ["Anual", "Mensual"])



    # --------------------------------------------------------
    # BLOQUE D: EDAD ACTUARIAL
    # --------------------------------------------------------

    edad_actuarial = calcular_edad_actuarial(
        fecha_nacimiento,
        fecha_efecto
    )

    st.divider()

    st.subheader("04. Resumen actuarial")

    col9, col10, col11 = st.columns(3)

    col9.metric(
        "Edad actuarial",
        f"{edad_actuarial} años"
    )

    col10.metric(
         "Edad Cobertura",
         f"{edad_cobertura} años"
     )
    
    col11.metric(
        "Duración",
        f"{duracion} años"
    )


    st.divider()

    # --------------------------------------------------------
    # BOTON DE COTIZACION
    # --------------------------------------------------------

    enviar = st.form_submit_button(
        "Guardar poliza en la base de datos",
        type="primary",
        use_container_width=True
    )



# ============================================================
# 5. VALIDACION Y REGISTRO
# ============================================================

if enviar:

    if fecha_nacimiento >= fecha_efecto:
        st.error(
            "La fecha de nacimiento debe ser anterior "
            "a la fecha de efecto."
        )

    elif edad_actuarial < 18:
        st.error(
            "La edad actuarial mínima permitida es de 18 años."
        )

    elif edad_actuarial > 80:
        st.error(
            "La edad actuarial máxima provisional es de 80 años."
        )

    elif capital_asegurado < 1000:
        st.error(
            "El capital mínimo asegurado es de 1.000 €."
        )

    else:

        nueva_poliza = {
            "producto": producto,
            "fecha_nacimiento": fecha_nacimiento,
            "edad_actuarial": edad_actuarial,
            "fecha_efecto": fecha_efecto,
            "duracion": duracion,
            "edad_cobertura": edad_cobertura,
            "capital_asegurado": capital_asegurado,
            "modalidad_pago": modalidad_pago,
            "tipo_de_pago": tipo_de_pago
        }

        st.session_state.polizas = pd.concat(
            [
                st.session_state.polizas,
                pd.DataFrame([nueva_poliza])
            ],
            ignore_index=True
        )

        st.success("Cotización registrada correctamente.")



# ============================================================
# 6. GESTION DE SOLICITUDES
# ============================================================

st.divider()

st.header("Gestión de Pólizas Registradas")

if not st.session_state.polizas.empty:


    # --------------------------------------------------------
    # TABLA DE SOLICITUDES
    # --------------------------------------------------------

    st.subheader("Histórico de polizas")

    st.dataframe(
        st.session_state.polizas,
        use_container_width=True,
        hide_index=True
    )


    # --------------------------------------------------------
    # ELIMINACION DE SOLICITUDES
    # --------------------------------------------------------

    st.divider()
    
    st.subheader("Eliminar poliza")

    indice_eliminar = st.selectbox(
        "Selecciona la cotización",
        st.session_state.polizas.index,
        format_func=lambda x: f"Cotización {x + 1}"
    )

    if st.button("Eliminar cotización"):
    
        st.session_state.polizas = (
            st.session_state.polizas
            .drop(index=indice_eliminar)
            .reset_index(drop=True)
        )
    
        st.success("Cotización eliminada correctamente.")
    
        st.rerun()
    
    else:
    
        st.info(
            "Todavía no hay solicitudes registradas."
        )




st.caption(
    "Life Insurance Analytics | Proyecto actuarial | MVP"
)
