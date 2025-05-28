import streamlit as st

from datetime import datetime
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from core.correlation_matrix_utils import generate_correlation_heatmap_plotly
except ImportError as e:
    st.error(f"Error importing from core.correlation_matrix_utils: {e}. \nEnsure the file exists in 'core' directory and 'core' has an __init__.py file. \nPYTHONPATH: {sys.path}")
    st.stop()

st.set_page_config(
    page_title="Correlation Matrix Analyzer",
    layout="wide"
)

st.title("Stock Correlation Matrix Analyzer")
st.markdown("""
**Interactive Stock Correlation Analysis**

This tool computes and visualizes the correlation matrix for the closing prices of selected stock tickers over a specified period.
Use the controls in the sidebar to select tickers and define the analysis window.
*   **High positive correlation (close to +1)** indicates that stocks tend to move in the same direction.
*   **High negative correlation (close to -1)** indicates that stocks tend to move in opposite directions.
*   **Correlation near 0** suggests a weak linear relationship between the movements of the stocks.

The heatmap is generated using `yfinance` for data and `Plotly` for interactive visualization.
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Analysis Parameters")

    if 'corr_matrix_start_date' not in st.session_state:
        st.session_state.corr_matrix_start_date = datetime(2023, 1, 1)
    if 'corr_matrix_end_date' not in st.session_state:
        st.session_state.corr_matrix_end_date = datetime.now().date()

    start_date_input = st.date_input("Start Date", value=st.session_state.corr_matrix_start_date, key="corr_matrix_start_date_widget")
    end_date_input = st.date_input("End Date", value=st.session_state.corr_matrix_end_date, key="corr_matrix_end_date_widget")

    valid_dates = True
    if start_date_input >= end_date_input:
        st.error("Error: End date must be after start date.")
        valid_dates = False
    else:

        st.session_state.corr_matrix_start_date = start_date_input
        st.session_state.corr_matrix_end_date = end_date_input

    interval_options = {"Daily": "1d", "Weekly": "1wk", "Monthly": "1mo"}
    selected_interval_key = st.selectbox(
        "Select Data Interval", 
        options=list(interval_options.keys()),
        key="corr_matrix_interval_selectbox_widget"
    )
    actual_interval = interval_options[selected_interval_key]

    available_tickers = sorted([
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "JPM", "V", "JNJ", "LLY", "PEP",
        "BTC-USD", "ETH-USD", "GC=F", "SI=F", "CL=F", "NG=F", "EURUSD=X", "GBPUSD=X", "USDJPY=X",
        "OR.PA", "MC.PA", "AI.PA", "BNP.PA", "SAN.PA", "GLE.PA", "ACA.PA", "KER.PA", "RMS.PA",
        "ADS.DE", "ALV.DE", "BAS.DE", "BAYN.DE", "BMW.DE", "MBG.DE", "VOW3.DE", "SAP.DE", "SIE.DE"
    ])
    default_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"] 
    default_tickers_valid = [t for t in default_tickers if t in available_tickers]
    if not default_tickers_valid and available_tickers:
        default_tickers_valid = available_tickers[:min(4, len(available_tickers))]
        
    selected_tickers = st.multiselect(
        "Select Tickers (min. 2)",
        options=available_tickers,
        default=default_tickers_valid,
        key="corr_matrix_tickers_multiselect_widget"
    )

run_analysis = st.sidebar.button("Generate Correlation Matrix", key="corr_matrix_run_button_widget", use_container_width=True)

if run_analysis:
    if not valid_dates:
        st.error("Please correct the date selection before generating the matrix.")

    else:
        correlation_fig, message = generate_correlation_heatmap_plotly(
            selected_tickers, start_date_input, end_date_input, actual_interval
        )
        
        if message:
            st.warning(message) 

        if correlation_fig:
            st.plotly_chart(correlation_fig, use_container_width=True)
        elif not message: 
            st.info("Could not generate the correlation matrix. Please check selections or data availability.")
            
elif not selected_tickers and not run_analysis: 
    st.info("Select tickers and parameters in the sidebar, then click 'Generate Correlation Matrix'.")

st.caption("Note: Correlation measures linear relationships and does not imply causation. Ensure selected tickers have overlapping historical data for meaningful results.")
st.markdown("---")
st.markdown("Developed by **Yanis Montacer**")
st.markdown("Connect with me: [LinkedIn](https://www.linkedin.com/in/yanis-m-44418b288/) | [GitHub](https://github.com/YanisMtcr)")