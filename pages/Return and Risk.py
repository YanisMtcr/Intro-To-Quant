import streamlit as st

from datetime import datetime

import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from core.return_risk_utils import calculate_return_risk_metrics_and_plot
except ImportError as e:
    st.error(f"Error importing from core.return_risk_utils: {e}. \nEnsure the file exists in 'core' directory and 'core' has an __init__.py file. \nPYTHONPATH: {sys.path}")
    st.stop()

interval_options = {"Daily": "1d", "Hourly": "1h", "Weekly": "1wk"}

st.set_page_config(
    page_title="Return and Risk Analyzer",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Return and Risk Analyzer")

st.markdown("""
**Return Distribution & Risk Metrics Analyzer**

This application provides an interactive tool to analyze the historical return distribution of a stock and key risk/return metrics.
It is designed for quantitative assessment, enabling users to:
*   Input any stock ticker symbol.
*   Define custom analysis periods (start and end dates).
*   Select the data interval (e.g., daily, hourly, weekly).
*   Visualize the return distribution histogram and an overlaid normal distribution curve.
*   Review key statistics such as mean return and standard deviation (volatility).

The tool utilizes `yfinance` for market data, `pandas` and `numpy` for data manipulation, `scipy` for statistical calculations, and `Plotly` for interactive charting, all presented within a `Streamlit` web interface.
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Analysis Parameters")
    
    ticker_list = sorted([
        "AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "AMZN", "META", "JPM", "V", "JNJ", "LLY", "PEP",
        "BTC-USD", "ETH-USD", "GC=F", "SI=F", "CL=F", "NG=F", "EURUSD=X", "GBPUSD=X", "USDJPY=X",
        "OR.PA", "MC.PA", "AI.PA", "BNP.PA", "SAN.PA", "GLE.PA", "ACA.PA", "KER.PA", "RMS.PA",
        "ADS.DE", "ALV.DE", "BAS.DE", "BAYN.DE", "BMW.DE", "MBG.DE", "VOW3.DE", "SAP.DE", "SIE.DE"
    ])

    ticker = st.text_input("Enter a ticker symbol (e.g., AAPL)", value="AAPL", key="return_risk_ticker_input")


    start_date = st.date_input("Start Date", value=datetime(2023, 1, 1), key="return_risk_start_date")
    end_date = st.date_input("End Date", value=datetime.now().date(), key="return_risk_end_date") 
    
    if start_date >= end_date:
        st.error("Error: End date must be after start date.")
        st.stop()

    selected_interval_display = st.selectbox("Select Data Interval", list(interval_options.keys()), key="return_risk_interval_select")
    actual_interval = interval_options[selected_interval_display]

if ticker:

    mean_return, std_return, fig, message = calculate_return_risk_metrics_and_plot(
        ticker, start_date, end_date, actual_interval, interval_options
    )
    
    if message and (mean_return is None or fig is None): 
        st.error(message)
    elif message: 
        st.warning(message)

    if mean_return is not None and std_return is not None and fig is not None:
        st.divider()
        st.subheader(f"Key Statistics for {ticker} ({selected_interval_display})") 
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label=f"{selected_interval_display} Mean Return", value=f"{mean_return:.2f}%")
        with col2:
            st.metric(label=f"{selected_interval_display} Std. Deviation (Risk)", value=f"{std_return:.2f}%")
        
        st.plotly_chart(fig, use_container_width=True)
    elif not message:
        st.info("Could not retrieve or process data. Please check parameters.")

else:
    st.info("Please enter a ticker symbol in the sidebar to begin analysis.")

st.caption("Disclaimer: All tools are for educational and illustrative purposes only. Not financial advice.")
st.markdown("---")
st.markdown("Developed by **Yanis Montacer**")
st.markdown("Connect with me: [LinkedIn](https://www.linkedin.com/in/yanis-m-44418b288/) | [GitHub](https://github.com/YanisMtcr)")


