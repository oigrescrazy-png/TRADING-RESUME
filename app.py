import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# Configuración para pantalla de celular
st.set_page_config(page_title="Escáner de Opciones", layout="wide", initial_sidebar_state="collapsed")

st.title("📊 Escáner Técnico y Noticias de Mercado")
st.caption(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

TICKERS = ["NVDA", "AMZN", "AAPL", "QQQ", "SPY", "GOOGL"]

# --- CÁLCULOS TÉCNICOS ---
def obtener_datos_tecnicos(ticker):
    stock = yf.Ticker(ticker)
    
    # 1. Datos Diarios (EMAs + Bollinger Diario)
    df_diario = stock.history(period="1y", interval="1d")
    if df_diario.empty:
        return None
    
    df_diario['EMA20'] = df_diario['Close'].ewm(span=20, adjust=False).mean()
    df_diario['EMA40'] = df_diario['Close'].ewm(span=40, adjust=False).mean()
    df_diario['EMA100'] = df_diario['Close'].ewm(span=100, adjust=False).mean()
    df_diario['EMA200'] = df_diario['Close'].ewm(span=200, adjust=False).mean()
    
    # Bollinger Diario (20, 2)
    sma20_d = df_diario['Close'].rolling(window=20).mean()
    std20_d = df_diario['Close'].rolling(window=20).std()
    df_diario['BB_Sup'] = sma20_d + (std20_d * 2)
    df_diario['BB_Inf'] = sma20_d - (std20_d * 2)

    # 2. Datos Intradía 1 hora
    df_1h = stock.history(period="1mo", interval="60m")
    if not df_1h.empty:
        sma20_1h = df_1h['Close'].rolling(window=20).mean()
        std20_1h = df_1h['Close'].rolling(window=20).std()
        df_1h['BB_Sup'] = sma20_1h + (std20_1h * 2)
        df_1h['BB_Inf'] = sma20_1h - (std20_1h * 2)
    
    # 3. Datos Intradía 15 min
    df_15m = stock.history(period="5d", interval="15m")
    if not df_15m.empty:
        sma20_15m = df_15m['Close'].rolling(window=20).mean()
        std20_15m = df_15m['Close'].rolling(window=20).std()
        df_15m['BB_Sup'] = sma20_15m + (std20_15m * 2)
        df_15m['BB_Inf'] = sma20_15m - (std20_15m * 2)

    # Estado de Bandas de Bollinger
    def evaluar_bollinger(df):
        if df.empty or len(df) < 20:
            return "Sin datos"
        ultimo_cierre = df['Close'].iloc[-1]
        bb_sup = df['BB_Sup'].iloc[-1]
        bb_inf = df['BB_Inf'].iloc[-1]
        ancho_banda = (bb_sup - bb_inf) / df['Close'].rolling(window=20).mean().iloc[-1]
        
        if ancho_banda < 0.03:
            return "🔥 Compresión (Squeeze)"
        elif ultimo_cierre >= bb_sup:
            return "📈 Ruptura Superior (Alcista)"
        elif ultimo_cierre <= bb_inf:
            return "📉 Sobreventa / Banda Inferior"
        else:
            return "Neutral (Dentro de bandas)"

    ultimo = df_diario.iloc[-1]
    precio = ultimo['Close']
    
    # Evaluación de la estructura de las 4 EMAs
    ema_alcista = ultimo['EMA20'] > ultimo['EMA40'] > ultimo['EMA100'] > ultimo['EMA200']
    ema_bajista = ultimo['EMA20'] < ultimo['EMA40'] < ultimo['EMA100'] < ultimo['EMA200']
    
    if ema_alcista:
        estado_emas = "🟢 Alineación Alcista (20 > 40 > 100 > 200)"
        sesgo = "CALL (Comprar Call)"
    elif ema_bajista:
        estado_emas = "🔴 Alineación Bajista (20 < 40 < 100 < 200)"
        sesgo = "PUT (Comprar Put)"
    else:
        estado_emas = "🟡 En Rango / Mixta"
        sesgo = "NEUTRAL / ESPERAR"

    return {
        "Ticker": ticker,
        "Precio": f"${precio:.2f}",
        "Sesgo": sesgo,
        "Estado EMAs": estado_emas,
        "EMA 20": f"${ultimo['EMA20']:.2f}",
        "EMA 40": f"${ultimo['EMA40']:.2f}",
        "EMA 100": f"${ultimo['EMA100']:.2f}",
        "EMA 200": f"${ultimo['EMA200']:.2f}",
        "BB 15 min": evaluar_bollinger(df_15m),
        "BB 1 Hora": evaluar_bollinger(df_1h),
        "BB Diario": evaluar_bollinger(df_diario),
        "Noticias": stock.news[:3] if stock.news else []
    }

# --- PESTAÑAS DE LA APLICACIÓN ---
tab1, tab2, tab3 = st.tabs(["📊 Escáner Técnico", "📰 Noticias y Fed", "🗓️ Calendario del Mercado"])

# PESTAÑA 1: ESCÁNER TÉCNICO
with tab1:
    st.subheader("Análisis de EMAs y Bandas de Bollinger Multitemporal")
    
    opcion_ticker = st.selectbox("Selecciona un símbolo:", ["TODOS"] + TICKERS)
    
    with st.spinner("Descargando datos del mercado en vivo..."):
        resultados = [obtener_datos_tecnicos(t) for t in TICKERS if obtener_datos_tecnicos(t) is not None]

    if opcion_ticker == "TODOS":
        datos_resumen = []
        for r in resultados:
            datos_resumen.append({
                "Acción / ETF": r["Ticker"],
                "Precio Actual": r["Precio"],
                "Estrategia Opciones": r["Sesgo"],
                "Bollinger (15 min)": r["BB 15 min"],
                "Bollinger (1 Hora)": r["BB 1 Hora"],
                "Bollinger (Diario)": r["BB Diario"],
                "Tendencia EMAs": r["Estado EMAs"]
            })
        st.dataframe(pd.DataFrame(datos_resumen), use_container_width=True)
    else:
        datos = next((r for r in resultados if r["Ticker"] == opcion_ticker), None)
        if datos:
            col1, col2, col3 = st.columns(3)
            col1.metric("Precio Actual", datos["Precio"])
            col2.metric("Sesgo Sugerido", datos["Sesgo"])
            col3.metric("Estructura de EMAs", datos["Estado EMAs"])
            
            st.markdown("### 🎯 Estado de Bandas de Bollinger")
            st.write(f"• **Marco de 15 minutos:** {datos['BB 15 min']}")
            st.write(f"• **Marco de 1 Hora:** {datos['BB 1 Hora']}")
            st.write(f"• **Marco Diario:** {datos['BB Diario']}")
            
            st.markdown("### 📏 Valores de EMAs Diarias")
            st.write(f"• **EMA 20:** {datos['EMA 20']}")
            st.write(f"• **EMA 40:** {datos['EMA 40']}")
            st.write(f"• **EMA 100:** {datos['EMA 100']}")
            st.write(f"• **EMA 200:** {datos['EMA 200']}")

# PESTAÑA 2: NOTICIAS
with tab2:
    st.subheader("📰 Titulares Relevantes de las Acciones")
    st.info("Noticias recientes que pueden impactar la volatilidad implícita (IV) y mover los precios.")
    
    for r in resultados:
        with st.expander(f"Noticias recientes de {r['Ticker']}"):
            if r["Noticias"]:
                for n in r["Noticias"]:
                    titulo = n.get('title', 'Sin título')
                    enlace = n.get('link', '#')
                    fuente = n.get('publisher', 'Fuente no especificada')
                    st.write(f"• **[{titulo}]({enlace})** - *{fuente}*")
            else:
                st.write("No hay noticias destacadas en este momento.")

# PESTAÑA 3: CALENDARIO MACROECONÓMICO
with tab3:
    st.subheader("🗓️ Eventos y Catalizadores Económicos Clave")
    st.warning("⚠️ Monitorea estos eventos para proteger tus contratos Call o Put antes de la apertura.")
    
    st.markdown("""
    * **Reuniones de la Fed (FOMC) / Discursos de Jerome Powell:** Definen el rumbo macro de los mercados e impactan fuertemente en QQQ y SPY.
    * **Datos de Inflación (CPI / PPI):** Reportes mensuales que causan saltos bruscos en el precio y en las primas de opciones.
    * **Reporte de Empleo (NFP):** Se publica el primer viernes de cada mes a las 8:30 AM (hora del Este).
    * **Reportes de Ganancias (Earnings):** Revisa las fechas exactas de entrega de resultados de NVDA, AMZN, AAPL y GOOGL para controlar el riesgo de caída de volatilidad (*IV Crush*).
    """)
