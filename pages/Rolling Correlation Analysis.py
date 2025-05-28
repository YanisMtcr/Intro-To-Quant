import streamlit as st
from datetime import datetime
import pandas as pd 
import sys
import os


current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir) 
core_path = os.path.join(project_root, "core")
if project_root not in sys.path:
    sys.path.insert(0, project_root) 

try:
    from core.rolling_correlation_utils import Correlation_data, calculate_correlation, plot_combined_correlation_plotly
except ImportError as e:
    st.error(f"Error importing from core.rolling_correlation_utils: {e}. \nEnsure the file exists in 'core' directory and 'core' has an __init__.py file. \nProject root: {project_root}\nPYTHONPATH: {sys.path}")
    st.stop()

st.set_page_config(
    page_title="Rolling Correlation Analyzer",
    layout="wide"
)

st.title("Rolling Correlation Analyzer")

st.markdown("""
**Dynamic Pair Correlation Analysis**

This application provides an interactive platform for visualizing the rolling correlation between two selected stock tickers.
It is designed for quantitative pairs trading analysis, allowing users to:
*   Select any two stock tickers for comparison.
*   Define custom analysis periods and data intervals.
*   Adjust parameters for rolling correlation calculation (window, MA window for bands, standard deviations).
*   Visualize combined stock prices alongside their rolling correlation, average correlation, and deviation bands.

The tool leverages `yfinance` for market data, `pandas` for data manipulation, and `Plotly` for interactive charting, all presented within a `Streamlit` interface.
""", unsafe_allow_html=True)

def get_sidebar_inputs():
    with st.sidebar:
        st.header("Analysis Parameters")

        ticker_options = sorted([
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "JPM", "V", "JNJ", "LLY", "PEP",
            "BTC-USD", "ETH-USD", "GC=F", "SI=F", "CL=F", "NG=F", "EURUSD=X", "GBPUSD=X", "USDJPY=X",
            "OR.PA", "MC.PA", "AI.PA", "BNP.PA", "SAN.PA", "GLE.PA", "ACA.PA", "KER.PA", "RMS.PA",
            "ADS.DE", "ALV.DE", "BAS.DE", "BAYN.DE", "BMW.DE", "MBG.DE", "VOW3.DE", "SAP.DE", "SIE.DE"
        ])
        default_ticker1 = "AAPL" if "AAPL" in ticker_options else ticker_options[0] if ticker_options else ""
        default_ticker2 = "MSFT" if "MSFT" in ticker_options and len(ticker_options) > 1 else ticker_options[1] if len(ticker_options) > 1 else ""
        if default_ticker1 == default_ticker2 and len(ticker_options)>1:
            default_ticker2 = ticker_options[1] if default_ticker1 == ticker_options[0] and len(ticker_options)>1 else ticker_options[0]

        ticker1 = st.selectbox("Select Ticker 1", options=ticker_options, index=ticker_options.index(default_ticker1) if default_ticker1 else 0, key="ticker1_roll_corr")
        ticker2 = st.selectbox("Select Ticker 2", options=ticker_options, index=ticker_options.index(default_ticker2) if default_ticker2 else 0, key="ticker2_roll_corr")

        start_date = st.date_input("Start Date", value=datetime(2022, 1, 1), key="start_date_roll_corr")
        end_date = st.date_input("End Date", value=datetime.now().date(), key="end_date_roll_corr")

        interval_options_map = {"Daily": "1d", "Weekly": "1wk", "Monthly": "1mo"}
        selected_interval_display = st.selectbox("Select Data Interval", options=list(interval_options_map.keys()), key="interval_roll_corr")
        actual_interval = interval_options_map[selected_interval_display]

        st.subheader("Correlation Parameters")
        corr_window = st.number_input("Rolling Correlation Window", min_value=5, max_value=200, value=30, step=5, key="corr_window_roll_corr")
        corr_avg_window = st.number_input("Correlation MA Window (for bands)", min_value=10, max_value=500, value=100, step=10, key="corr_avg_window_roll_corr")
        corr_std_dev = st.number_input("Std. Deviations for Bands", min_value=0.5, max_value=3.0, value=1.0, step=0.1, key="corr_std_dev_roll_corr")
        
        run_button = st.button("Run Analysis", key="run_roll_corr_analysis", use_container_width=True)

    return ticker1, ticker2, start_date, end_date, actual_interval, corr_window, corr_avg_window, corr_std_dev, run_button

ticker1, ticker2, start_date, end_date, actual_interval, corr_window, corr_avg_window, corr_std_dev, run_button = get_sidebar_inputs()

if run_button:
    if not ticker1 or not ticker2:
        st.warning("Please select two tickers.")
    elif ticker1 == ticker2:
        st.warning("Please select two different tickers for rolling correlation analysis.")
    elif start_date >= end_date:
        st.error("Error: End date must be after start date.")
    else:
        st.subheader(f"Rolling Correlation Analysis: {ticker1} vs {ticker2}")
        st.markdown(f"**Period:** `{start_date.strftime('%Y-%m-%d')}` to `{end_date.strftime('%Y-%m-%d')}` | **Interval:** `{actual_interval}` | **Corr Window:** `{corr_window}`")
        
        price_data_df = Correlation_data(ticker1, ticker2, start_date, end_date, actual_interval)
        
        if not price_data_df.empty and price_data_df.shape[0] > 1 and price_data_df.shape[1] == 2:
            if price_data_df.isnull().values.any():
                st.warning("Price data contains NaNs. Results might be affected. Consider a different period or tickers with more complete data. Attempting to clean NaNs.")
                price_data_df = price_data_df.dropna()
            
            if price_data_df.shape[0] < corr_window:
                st.error(f"Not enough data points ({price_data_df.shape[0]}) after cleaning for the rolling correlation window ({corr_window}). Please select a longer period or a shorter window.")
            else:
                correlation_calcs_df = calculate_correlation(price_data_df, window=corr_window, std_dev=corr_std_dev, wide_window=corr_avg_window)
                
                if not correlation_calcs_df.empty:
                    st.markdown("### Combined Price and Rolling Correlation Chart")
                    # The plot function is also now in the utils module
                    fig_combined = plot_combined_correlation_plotly(price_data_df, correlation_calcs_df)
                    if fig_combined is not None and fig_combined.data: 
                        st.plotly_chart(fig_combined, use_container_width=True)
                    else:
                        st.warning("Could not generate the combined correlation plot. This might happen if correlation data is empty or plot function returned None.")

                    with st.expander("View Processed Correlation Data Details"):
                        st.dataframe(correlation_calcs_df)
                    with st.expander("View Price Data Used (after cleaning)"):
                        st.dataframe(price_data_df)
                else:
                    st.error("Could not calculate correlation data. This might be due to insufficient overlapping data for the selected tickers and period, or very short window parameters relative to available data.")
        elif price_data_df.empty:
             st.error(f"Failed to fetch price data for {ticker1} and/or {ticker2}. Please check ticker validity, data availability for the period, and interval selection.")
        else:
            st.error(f"Fetched price data for {ticker1} and {ticker2} is insufficient or not in the expected format (e.g., less than 2 columns or 2 rows). Data shape: {price_data_df.shape}")
else:
    st.info("Select parameters in the sidebar and click 'Run Analysis'.")

st.caption("Disclaimer: All tools are for educational and illustrative purposes only. Not financial advice.")
st.markdown("---")
st.markdown("Developed by **Yanis Montacer**")
st.markdown("Connect with me: [LinkedIn](https://www.linkedin.com/in/yanis-m-44418b288/) | [GitHub](https://github.com/YanisMtcr)")

