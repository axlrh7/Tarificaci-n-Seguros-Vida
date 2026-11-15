
# ============================================================
# PROYECTO ACTUARIAL
# COTIZADOR DE SEGUROS DE VIDA - MVP
# ============================================================

import streamlit as st
import pandas as pd
from datetime import date, timedelta

# ============================================================
# 1. CONFIGURACION
# ============================================================

st.set_page_config(
    page_title="Life Insurance Analytics",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Life Insurance Analytics")
st.caption("Cotizador actuarial | Seguro temporal de fallecimiento")

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
        fecha_nacimiento, fecha_efecto.year
    )

    if ultimo_cumpleanos > fecha_efecto:
        edad -= 1

    siguiente_cumpleanos = cumpleanos_en_anio(
        fecha_nacimiento, fecha_efecto.year + 1
    )

    dias_desde = (fecha_efecto - ultimo_cumpleanos).days
    dias_hasta = (siguiente_cumpleanos - fecha_efecto).days

    # Redondeo al cumpleaños más próximo.
    # En caso de empate se conserva la edad cumplida.

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
    "solicitud",
    "producto",
    "fecha_nacimiento",
    "edad_actuarial",
    "fecha_efecto",
    "fecha_vencimiento",
    "duracion",
    "capital_asegurado",
    "modalidad_pago"
]

if "polizas" not in st.session_state:

    st.session_state.polizas = pd.DataFrame(
        columns=columnas
    )


# ============================================================
# 4. FORMULARIO DE COTIZACION
# ============================================================

st.header("Nueva cotización")

with st.form("formulario_cotizacion"):

    # --------------------------------------------------------
    # BLOQUE A: DATOS DEL ASEGURADO
    # --------------------------------------------------------

    st.subheader("01. Datos del asegurado")

    col1, col2 = st.columns(2)

    with col1:

        solicitud = st.text_input(
            "Número de solicitud",
            placeholder="Ej. SOL-0001"
        )

        fecha_nacimiento = st.date_input(
            "Fecha de nacimiento",
            value=date(1989, 5, 15),
            min_value=date(1900, 1, 1),
            max_value=date.today()
        )

    with col2:

        fecha_efecto = st.date_input(
            "Fecha de efecto",
            value=date.today(),
            min_value=date.today()
        )

        producto = st.selectbox(
            "Producto",
            ["Temporal de fallecimiento"]
        )

    # --------------------------------------------------------
    # BLOQUE B: CARACTERISTICAS DEL SEGURO
    # --------------------------------------------------------

    st.divider()
    st.subheader("02. Características del seguro")

    col3, col4 = st.columns(2)

    with col3:

        capital_asegurado = st.number_input(
            "Capital asegurado (€)",
            min_value=1000.0,
            value=100000.0,
            step=5000.0
        )

    with col4:

        duracion = st.selectbox(
            "Duración del seguro (años)",
            list(range(1, 41)),
            index=19
        )

    fecha_vencimiento = sumar_anios(
        fecha_efecto, duracion
    )

    # --------------------------------------------------------
    # BLOQUE C: MODALIDAD DE PAGO
    # --------------------------------------------------------

    st.divider()
    st.subheader("03. Modalidad de pago")

    modalidad_pago = st.radio(
        "Modalidades que se desean cotizar",
        ["Ambas", "Anual", "Mensual"],
        horizontal=True,
        index=0
    )

    # --------------------------------------------------------
    # BLOQUE D: EDAD ACTUARIAL
    # --------------------------------------------------------

    edad_actuarial = calcular_edad_actuarial(
        fecha_nacimiento,
        fecha_efecto
    )

    st.divider()

    col5, col6, col7 = st.columns(3)

    col5.metric(
        "Edad actuarial",
        f"{edad_actuarial} años"
    )

    col6.metric(
        "Duración",
        f"{duracion} años"
    )

    col7.metric(
        "Vencimiento",
        fecha_vencimiento.strftime("%d/%m/%Y")
    )

    # --------------------------------------------------------
    # BOTON DE COTIZACION
    # --------------------------------------------------------

    enviar = st.form_submit_button(
        "Generar solicitud de cotización",
        type="primary",
        use_container_width=True
    )


# ============================================================
# 5. VALIDACION Y REGISTRO
# ============================================================

if enviar:

    if not solicitud.strip():

        st.error("Introduce un número de solicitud.")

    elif fecha_nacimiento >= fecha_efecto:

        st.error(
            "La fecha de nacimiento debe ser anterior "
            "a la fecha de efecto."
        )

    elif fecha_efecto < date.today():

        st.error("La fecha de efecto no puede estar en el pasado.")

    elif edad_actuarial < 18:

        st.error("La edad del asegurado debe ser de al menos 18 años.")

    elif solicitud in st.session_state.polizas["solicitud"].values:

        st.error("Esta solicitud ya existe.")

    else:

        nueva_poliza = {
            "solicitud": solicitud,
            "producto": producto,
            "fecha_nacimiento": fecha_nacimiento,
            "edad_actuarial": edad_actuarial,
            "fecha_efecto": fecha_efecto,
            "fecha_vencimiento": fecha_vencimiento,
            "duracion": duracion,
            "capital_asegurado": capital_asegurado,
            "modalidad_pago": modalidad_pago
        }

        st.session_state.polizas = pd.concat(
            [
                st.session_state.polizas,
                pd.DataFrame([nueva_poliza])
            ],
            ignore_index=True
        )

        st.success("Solicitud registrada correctamente.")


# ============================================================
# 6. GESTION DE SOLICITUDES
# ============================================================

st.divider()

st.header("Solicitudes registradas")

if not st.session_state.polizas.empty:

    st.dataframe(
        st.session_state.polizas,
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        f"Total de solicitudes: "
        f"{len(st.session_state.polizas)}"
    )

else:

    st.info("Todavía no hay solicitudes registradas.")
