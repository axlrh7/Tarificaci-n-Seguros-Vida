
# ============================================================
# PROYECTO ACTUARIAL
# COTIZADOR DE SEGUROS DE VIDA - MVP
# TABLA PASEM2019 - SEGUNDO ORDEN
# ============================================================

import streamlit as st
import pandas as pd

from datetime import date
from io import BytesIO


# ============================================================
# 1. CONFIGURACION
# ============================================================

st.set_page_config(
    page_title="Cotizador actuarial de seguros de Vida",
    layout="wide"
)

st.title("Cotizador actuarial de seguros de Vida")
st.caption("Life Insurance Analytics | Proyecto actuarial")

st.divider()


# ============================================================
# 2. FUNCIONES AUXILIARES
# ============================================================

def cumpleanos_en_anio(fecha_nacimiento, anio):

    try:
        return fecha_nacimiento.replace(year=anio)

    except ValueError:
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

    dias_desde = (
        fecha_efecto - ultimo_cumpleanos
    ).days

    dias_hasta = (
        siguiente_cumpleanos - fecha_efecto
    ).days

    # Redondeo al cumpleaños más próximo
    if dias_hasta < dias_desde:
        edad += 1

    return edad


# ============================================================
# 3. TABLA DE MORTALIDAD PASEM2019
# ============================================================

def preparar_tabla_pasem(archivo, sexo):

    """
    Lee el Excel oficial facilitado para el proyecto.

    Hoja:
    Anexo 1.2 y Anexo 1.3

    Estructura:
    Fila 5: Título de la tabla
    Fila 6: Mujeres / Hombres
    Fila 8: Descripción de qx
    Fila 9 en adelante: Edades y tasas

    Las tasas están expresadas en tanto por mil.
    Se convierten a probabilidades dividiendo entre 1000.
    """

    df = pd.read_excel(
        archivo,
        sheet_name="Anexo 1.2 y Anexo 1.3",
        header=None
    )

    if df.shape[1] < 3:
        raise ValueError(
            "El Excel no contiene las columnas esperadas."
        )

    titulo = str(df.iloc[4, 1]).strip()

    if "PASEM2019_General_2ndo.orden" not in titulo:

        raise ValueError(
            "No se ha encontrado la tabla PASEM2019 "
            "de segundo orden."
        )

    # Seleccionar columna según sexo
    if sexo == "Mujeres":
        columna = 1

    elif sexo == "Hombres":
        columna = 2

    else:
        raise ValueError("Sexo no reconocido.")

    # Extraer edades y tasas
    tabla = df.iloc[8:, [0, columna]].copy()

    tabla.columns = [
        "edad",
        "qx_mil"
    ]

    tabla["edad"] = pd.to_numeric(
        tabla["edad"],
        errors="coerce"
    )

    tabla["qx_mil"] = pd.to_numeric(
        tabla["qx_mil"],
        errors="coerce"
    )

    tabla = tabla.dropna()

    tabla["edad"] = tabla["edad"].astype(int)

    tabla = tabla.sort_values(
        "edad"
    ).reset_index(drop=True)

    # Comprobar edades disponibles
    edades_esperadas = list(range(0, 121))

    if tabla["edad"].tolist() != edades_esperadas:

        raise ValueError(
            "La tabla debe contener las edades consecutivas "
            "de 0 a 120."
        )

    if tabla["edad"].duplicated().any():

        raise ValueError(
            "Existen edades duplicadas."
        )

    # Validar tasas en tanto por mil
    if (
        (tabla["qx_mil"] < 0).any()
        or (tabla["qx_mil"] > 1000).any()
    ):

        raise ValueError(
            "Se han encontrado tasas fuera del rango "
            "válido de tanto por mil."
        )

    # Conversión de tanto por mil a probabilidad
    tabla["qx"] = tabla["qx_mil"] / 1000

    if (
        (tabla["qx"] < 0).any()
        or (tabla["qx"] > 1).any()
    ):

        raise ValueError(
            "Existen probabilidades de mortalidad inválidas."
        )

    return tabla[
        ["edad", "qx_mil", "qx"]
    ]


# ============================================================
# 4. MOTOR DE CALCULO ACTUARIAL
# ============================================================

def calcular_prima_vida_entera(
    edad,
    capital,
    tipo_interes,
    tipo_pago,
    tabla_mortalidad
):

    """
    Modelo actuarial MVP:

    - Seguro de Vida Entera.
    - Capital constante.
    - Prestación al final del año de fallecimiento.
    - Prima pura nivelada.
    - Sin gastos ni recargos comerciales.

    PREPAGABLE:
    Prima al inicio del año mientras el asegurado viva.

    POSTPAGABLE:
    Prima al final del año si el asegurado sobrevive.
    """

    tabla = tabla_mortalidad.set_index("edad")

    edad_maxima = int(tabla.index.max())

    if edad not in tabla.index:

        raise ValueError(
            f"La edad {edad} no está disponible "
            "en la tabla de mortalidad."
        )

    if capital <= 0:

        raise ValueError(
            "El capital debe ser positivo."
        )

    if tipo_interes < 0:

        raise ValueError(
            "El tipo de interés no puede ser negativo."
        )

    v = 1 / (1 + tipo_interes)

    supervivencia = 1.0

    va_prestaciones = 0.0

    va_unidad_primas = 0.0

    resultados = []

    # --------------------------------------------------------
    # RECORRIDO ANUAL DE LA POLIZA
    # --------------------------------------------------------

    for k in range(
        0,
        edad_maxima - edad + 1
    ):

        edad_actual = edad + k

        qx = float(
            tabla.loc[edad_actual, "qx"]
        )

        px = 1 - qx

        supervivencia_inicio = supervivencia

        supervivencia_final = (
            supervivencia_inicio * px
        )

        # ----------------------------------------------------
        # PROBABILIDAD DE FALLECIMIENTO
        # ----------------------------------------------------

        prob_fallecimiento = (
            supervivencia_inicio * qx
        )

        # ----------------------------------------------------
        # PRESTACION ESPERADA
        # ----------------------------------------------------

        prestacion_esperada = (
            capital * prob_fallecimiento
        )

        descuento_prestacion = (
            v ** (k + 1)
        )

        va_prestacion = (
            prestacion_esperada
            * descuento_prestacion
        )

        va_prestaciones += va_prestacion

        # ----------------------------------------------------
        # FACTOR DE PRIMA
        # ----------------------------------------------------

        if tipo_pago == "Prepagable":

            prob_pago_prima = (
                supervivencia_inicio
            )

            descuento_prima = (
                v ** k
            )

        else:

            prob_pago_prima = (
                supervivencia_final
            )

            descuento_prima = (
                v ** (k + 1)
            )

        factor_prima = (
            prob_pago_prima
            * descuento_prima
        )

        va_unidad_primas += factor_prima

        # ----------------------------------------------------
        # REGISTRO DE FLUJOS
        # ----------------------------------------------------

        resultados.append({

            "Año": k + 1,

            "Edad": edad_actual,

            "qx": qx,

            "px": px,

            "Supervivencia": supervivencia_inicio,

            "Prob. fallecimiento": prob_fallecimiento,

            "Prestación esperada (€)": prestacion_esperada,

            "VA prestación (€)": va_prestacion,

            "Factor prima": factor_prima,

            "Prob. supervivencia final": supervivencia_final

        })

        supervivencia = supervivencia_final

        # Extinción de la población asegurada
        if qx == 1:
            break

    # --------------------------------------------------------
    # CALCULO DE PRIMA PURA
    # --------------------------------------------------------

    if va_unidad_primas <= 0:

        raise ValueError(
            "El valor actual de las primas es cero."
        )

    prima_anual = (
        va_prestaciones / va_unidad_primas
    )

    # --------------------------------------------------------
    # TABLA DE FLUJOS CORREGIDA
    # --------------------------------------------------------

    df_resultados = pd.DataFrame(resultados)

    # Probabilidad de pago de prima
    if tipo_pago == "Prepagable":

        df_resultados["Prob. pago prima"] = (
            df_resultados["Supervivencia"]
        )

    else:

        df_resultados["Prob. pago prima"] = (
            df_resultados["Prob. supervivencia final"]
        )

    # Prima esperada sin descuento
    df_resultados["Prima esperada (€)"] = (
        df_resultados["Prob. pago prima"]
        * prima_anual
    )

    # Valor actual de la prima
    df_resultados["VA prima (€)"] = (
        df_resultados["Factor prima"]
        * prima_anual
    )

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    return {

        "prima_anual": prima_anual,

        "prima_mensual_equivalente": (
            prima_anual / 12
        ),

        "va_prestaciones": va_prestaciones,

        "va_unidad_primas": va_unidad_primas,

        "tabla_flujos": df_resultados

    }


# ============================================================
# 5. ALMACENAMIENTO DE POLIZAS
# ============================================================

columnas = [

    "producto",
    "sexo",
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

    st.session_state.polizas = pd.DataFrame(
        columns=columnas
    )


# ============================================================
# 6. FORMULARIO DE COTIZACION
# ============================================================

st.header("01. Nueva tarificación")

with st.form("formulario"):

    # --------------------------------------------------------
    # DATOS DEL ASEGURADO
    # --------------------------------------------------------

    st.subheader("Datos del asegurado")

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

        sexo = st.selectbox(
            "Sexo",
            ["Mujeres", "Hombres"]
        )

    with col4:

        producto = st.selectbox(
            "Producto",
            ["Vida Entera"]
        )

    # --------------------------------------------------------
    # CARACTERISTICAS DEL SEGURO
    # --------------------------------------------------------

    st.divider()

    st.subheader("Características del seguro")

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
            "Edad cobertura",
            min_value=18,
            max_value=120,
            value=60,
            step=1
        )

    with col8:

        modalidad_pago = st.selectbox(
            "Modalidad de pago",
            ["Anual", "Mensual"]
        )

    # --------------------------------------------------------
    # TIPO DE PAGO
    # --------------------------------------------------------

    st.divider()

    tipo_de_pago = st.selectbox(
        "Momento de pago de la prima",
        ["Prepagable", "Postpagable"]
    )

    # --------------------------------------------------------
    # RESUMEN ACTUARIAL
    # --------------------------------------------------------

    edad_actuarial = calcular_edad_actuarial(
        fecha_nacimiento,
        fecha_efecto
    )

    st.divider()

    st.subheader("Resumen actuarial")

    col9, col10, col11 = st.columns(3)

    col9.metric(
        "Edad actuarial",
        f"{edad_actuarial} años"
    )

    col10.metric(
        "Edad cobertura",
        f"{edad_cobertura} años"
    )

    col11.metric(
        "Duración",
        f"{duracion} años"
    )

    st.divider()

    enviar = st.form_submit_button(
        "Registrar póliza",
        type="primary",
        use_container_width=True
    )


# ============================================================
# 7. VALIDACION Y REGISTRO
# ============================================================

if enviar:

    if fecha_nacimiento >= fecha_efecto:

        st.error(
            "La fecha de nacimiento debe ser anterior "
            "a la fecha de efecto."
        )

    elif edad_actuarial < 18:

        st.error(
            "La edad mínima permitida es 18 años."
        )

    elif edad_actuarial > 80:

        st.error(
            "La edad máxima provisional es 80 años."
        )

    elif capital_asegurado < 1000:

        st.error(
            "El capital mínimo es 1.000 €."
        )

    else:

        nueva_poliza = {

            "producto": producto,

            "sexo": sexo,

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

        st.success(
            "Póliza registrada correctamente."
        )


# ============================================================
# 8. CARGA DE TABLA DE MORTALIDAD
# ============================================================

st.divider()

st.header("02. Hipótesis biométricas")

st.markdown(
    """
    **Tabla de mortalidad: PASEM2019 - Segundo orden**

    Fuente: Anexo facilitado para el proyecto actuarial.

    Los valores originales están expresados en tanto por mil.
    El sistema los convierte automáticamente a probabilidades.
    """
)

archivo_mortalidad = st.file_uploader(
    "Subir Excel de tablas de mortalidad",
    type=["xlsx"],
    key="tabla_mortalidad"
)

tabla_mortalidad = None

if archivo_mortalidad is not None:

    try:

        sexo_tabla = st.selectbox(
            "Serie biométrica",
            ["Mujeres", "Hombres"],
            key="sexo_tabla"
        )

        tabla_mortalidad = preparar_tabla_pasem(
            archivo_mortalidad,
            sexo_tabla
        )

        st.success(
            "Tabla PASEM2019 cargada y validada correctamente."
        )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Edad inicial",
            tabla_mortalidad["edad"].min()
        )

        col2.metric(
            "Edad final",
            tabla_mortalidad["edad"].max()
        )

        col3.metric(
            "Número de edades",
            len(tabla_mortalidad)
        )

        with st.expander(
            "Consultar tabla de mortalidad"
        ):

            st.dataframe(
                tabla_mortalidad,
                use_container_width=True,
                hide_index=True
            )

    except Exception as e:

        st.error(
            f"Error al procesar la tabla: {e}"
        )


# ============================================================
# 9. CALCULO ACTUARIAL
# ============================================================

st.divider()

st.header("03. Cálculo de la prima de riesgo")

if not st.session_state.polizas.empty:

    # --------------------------------------------------------
    # SELECCION DE POLIZA
    # --------------------------------------------------------

    st.subheader("Seleccionar póliza")

    indice_poliza = st.selectbox(
        "Selecciona la cotización",
        st.session_state.polizas.index,
        format_func=lambda x: (
            f"Cotización {x + 1} | "
            f"{st.session_state.polizas.loc[x, 'sexo']} | "
            f"Edad "
            f"{st.session_state.polizas.loc[x, 'edad_actuarial']} | "
            f"Capital "
            f"{st.session_state.polizas.loc[x, 'capital_asegurado']:,.2f} €"
        ),
        key="poliza_calculo"
    )

    poliza = st.session_state.polizas.loc[
        indice_poliza
    ]

    # --------------------------------------------------------
    # DATOS DE LA POLIZA
    # --------------------------------------------------------

    st.subheader("Datos de la póliza")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Edad actuarial",
        f"{poliza['edad_actuarial']} años"
    )

    col2.metric(
        "Sexo",
        poliza["sexo"]
    )

    col3.metric(
        "Capital asegurado",
        f"{poliza['capital_asegurado']:,.2f} €"
    )

    col4.metric(
        "Tipo de pago",
        poliza["tipo_de_pago"]
    )

    # --------------------------------------------------------
    # COMPROBAR SEXO
    # --------------------------------------------------------

    if archivo_mortalidad is not None:

        if sexo_tabla != poliza["sexo"]:

            st.warning(
                "La serie biométrica seleccionada no coincide "
                "con el sexo registrado en la póliza."
            )

    # --------------------------------------------------------
    # HIPOTESIS FINANCIERA
    # --------------------------------------------------------

    st.divider()

    st.subheader("Hipótesis financieras")

    tipo_interes = st.number_input(
        "Tipo de interés técnico anual (%)",
        min_value=0.0,
        max_value=20.0,
        value=2.0,
        step=0.25,
        format="%.2f"
    )

    tipo_interes_decimal = (
        tipo_interes / 100
    )

    # --------------------------------------------------------
    # BOTON DE CALCULO
    # --------------------------------------------------------

    calcular = st.button(
        "Calcular prima pura",
        type="primary",
        use_container_width=True
    )

    if calcular:

        if tabla_mortalidad is None:

            st.error(
                "Primero debes cargar una tabla "
                "de mortalidad válida."
            )

        elif sexo_tabla != poliza["sexo"]:

            st.error(
                "La serie biométrica no coincide con "
                "el sexo de la póliza."
            )

        else:

            try:

                resultado = calcular_prima_vida_entera(

                    edad=int(
                        poliza["edad_actuarial"]
                    ),

                    capital=float(
                        poliza["capital_asegurado"]
                    ),

                    tipo_interes=tipo_interes_decimal,

                    tipo_pago=poliza["tipo_de_pago"],

                    tabla_mortalidad=tabla_mortalidad

                )

                st.session_state.resultado_calculo = resultado

                st.session_state.datos_calculo = {

                    "indice_poliza": int(indice_poliza),

                    "sexo": sexo_tabla,

                    "tipo_interes": tipo_interes,

                    "tabla": "PASEM2019 - Segundo orden"

                }

                st.success(
                    "Cálculo actuarial realizado correctamente."
                )

            except Exception as e:

                st.error(
                    f"Error en el cálculo actuarial: {e}"
                )

else:

    st.info(
        "Primero debes registrar una póliza "
        "en el formulario."
    )


# ============================================================
# 10. PRESENTACION DE RESULTADOS
# ============================================================

if "resultado_calculo" in st.session_state:

    resultado = st.session_state.resultado_calculo

    datos_calculo = st.session_state.datos_calculo

    st.divider()

    st.header("04. Resultado de la tarificación")

    if (
        datos_calculo["indice_poliza"]
        not in st.session_state.polizas.index
    ):

        st.warning(
            "La póliza asociada al cálculo ya no existe."
        )

    else:

        poliza_resultado = st.session_state.polizas.loc[
            datos_calculo["indice_poliza"]
        ]

        prima_anual = resultado["prima_anual"]

        prima_mensual = resultado[
            "prima_mensual_equivalente"
        ]

        # ----------------------------------------------------
        # PRIMA SEGUN MODALIDAD
        # ----------------------------------------------------

        if poliza_resultado["modalidad_pago"] == "Anual":

            prima_mostrada = prima_anual

            texto_prima = "Prima anual pura"

        else:

            prima_mostrada = prima_mensual

            texto_prima = "Prima mensual equivalente"

        col1, col2, col3 = st.columns(3)

        col1.metric(
            texto_prima,
            f"{prima_mostrada:,.2f} €"
        )

        col2.metric(
            "Prima anual",
            f"{prima_anual:,.2f} €"
        )

        col3.metric(
            "Prima mensual equivalente",
            f"{prima_mensual:,.2f} €"
        )

        st.caption(
            "La prima mensual es una aproximación aritmética "
            "de la prima anual dividida entre doce."
        )

        # ----------------------------------------------------
        # DESGLOSE ACTUARIAL
        # ----------------------------------------------------

        st.subheader("Desglose actuarial")

        col4, col5 = st.columns(2)

        col4.metric(
            "VA de las prestaciones",
            f"{resultado['va_prestaciones']:,.2f} €"
        )

        col5.metric(
            "VA de la unidad de primas",
            f"{resultado['va_unidad_primas']:,.6f}"
        )

        if poliza_resultado["tipo_de_pago"] == "Prepagable":

            st.latex(
                r"P = \frac{C \cdot A_x}{\ddot{a}_x}"
            )

        else:

            st.latex(
                r"P = \frac{C \cdot A_x}{a_x}"
            )

        st.caption(
            "El denominador representa el valor actual "
            "de la unidad de primas según el calendario "
            "de pago seleccionado."
        )

        # ----------------------------------------------------
        # TABLA DE FLUJOS
        # ----------------------------------------------------

        df_flujos = resultado["tabla_flujos"]

        st.divider()

        st.header("05. Flujo actuarial de la póliza")

        st.subheader(
            "Prestaciones y primas esperadas"
        )

        st.line_chart(
            df_flujos.set_index("Año")[
                [
                    "Prestación esperada (€)",
                    "Prima esperada (€)"
                ]
            ]
        )

        st.caption(
            """
            Las prestaciones esperadas se obtienen multiplicando
            el capital asegurado por la probabilidad de fallecimiento
            de cada año.

            Las primas esperadas se ponderan por la probabilidad
            de que la prima sea pagada.
            """
        )

        # ----------------------------------------------------
        # VALORES ACTUALES
        # ----------------------------------------------------

        st.subheader(
            "Valores actuales de prestaciones y primas"
        )

        st.line_chart(
            df_flujos.set_index("Año")[
                [
                    "VA prestación (€)",
                    "VA prima (€)"
                ]
            ]
        )

        # ----------------------------------------------------
        # SUPERVIVENCIA
        # ----------------------------------------------------

        st.subheader(
            "Evolución de la supervivencia"
        )

        st.line_chart(
            df_flujos.set_index("Edad")[
                ["Supervivencia"]
            ]
        )

        # ----------------------------------------------------
        # DETALLE ANUAL
        # ----------------------------------------------------

        with st.expander(
            "Consultar detalle anual del cálculo"
        ):

            st.dataframe(
                df_flujos,
                use_container_width=True,
                hide_index=True
            )

        # ----------------------------------------------------
        # DESCARGA EXCEL
        # ----------------------------------------------------

        st.divider()

        st.subheader(
            "Exportar cálculo actuarial"
        )

        salida = BytesIO()

        with pd.ExcelWriter(
            salida,
            engine="openpyxl"
        ) as writer:

            df_flujos.to_excel(
                writer,
                sheet_name="Flujos actuariales",
                index=False
            )

            resumen = pd.DataFrame({

                "Concepto": [

                    "Producto",
                    "Sexo",
                    "Edad actuarial",
                    "Capital asegurado",
                    "Tabla de mortalidad",
                    "Tipo de interés técnico",
                    "Tipo de pago",
                    "Prima anual pura",
                    "Prima mensual equivalente",
                    "VA prestaciones",
                    "VA unidad de primas"

                ],

                "Valor": [

                    poliza_resultado["producto"],

                    poliza_resultado["sexo"],

                    poliza_resultado["edad_actuarial"],

                    poliza_resultado["capital_asegurado"],

                    datos_calculo["tabla"],

                    datos_calculo["tipo_interes"],

                    poliza_resultado["tipo_de_pago"],

                    prima_anual,

                    prima_mensual,

                    resultado["va_prestaciones"],

                    resultado["va_unidad_primas"]

                ]

            })

            resumen.to_excel(
                writer,
                sheet_name="Resumen",
                index=False
            )

        st.download_button(

            label="Descargar cálculo actuarial en Excel",

            data=salida.getvalue(),

            file_name="resultado_cotizacion_actuarial.xlsx",

            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),

            use_container_width=True

        )


# ============================================================
# 11. HISTORICO DE POLIZAS
# ============================================================

st.divider()

st.header("06. Histórico de pólizas")

if not st.session_state.polizas.empty:

    st.subheader(
        "Solicitudes registradas"
    )

    st.dataframe(
        st.session_state.polizas,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader(
        "Eliminar póliza"
    )

    indice_eliminar = st.selectbox(
        "Selecciona la póliza",
        st.session_state.polizas.index,
        format_func=lambda x: (
            f"Cotización {x + 1}"
        ),
        key="eliminar_poliza"
    )

    if st.button(
        "Eliminar póliza",
        type="secondary"
    ):

        st.session_state.polizas = (
            st.session_state.polizas
            .drop(index=indice_eliminar)
            .reset_index(drop=True)
        )

        if "resultado_calculo" in st.session_state:

            st.session_state.pop(
                "resultado_calculo"
            )

            st.session_state.pop(
                "datos_calculo"
            )

        st.success(
            "Póliza eliminada correctamente."
        )

        st.rerun()

else:

    st.info(
        "Todavía no hay pólizas registradas."
    )


# ============================================================
# 12. PIE DE PAGINA
# ============================================================

st.divider()

st.caption(
    "Life Insurance Analytics | Proyecto actuarial | MVP"
)
