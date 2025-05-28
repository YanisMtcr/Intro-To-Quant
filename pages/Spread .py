import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from core.spread_utils import calculate_price_spread_and_signals, create_spread_analysis_charts_plotly
except ImportError as e:
    st.error(f"Error importing from core.spread_utils: {e}. \nEnsure the file exists in 'core' directory and 'core' has an __init__.py file. \nPYTHONPATH: {sys.path}")
    st.stop()

st.set_page_config(
    page_title="Interactive Spread Analysis",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Interactive Price Spread Analysis & Backtest")

st.markdown("""
**Analyze and Backtest Price Spreads Between Two Assets**

This tool allows you to:
1.  Calculate the historical price spread between two selected assets (`Asset2_Price - Beta * Asset1_Price`). Beta is derived from a linear regression of `Asset2_Price` on `Asset1_Price` over the chosen period.
2.  Visualize the spread, its rolling mean, and its Z-score.
3.  Backtest a simple mean-reversion strategy based on Z-score thresholds:
    *   **Enter Long Spread** (Buy Asset2, Sell Beta * Asset1) when Z-score crosses *below* a lower band.
    *   **Enter Short Spread** (Sell Asset2, Buy Beta * Asset1) when Z-score crosses *above* an upper band.
    *   **Exit Position** when Z-score crosses towards zero, passing an exit band.
4.  View the cumulative P&L of the strategy and a list of individual trades.

Use the sidebar to configure assets, date range, Z-score parameters, and run the analysis.
""", unsafe_allow_html=True)


with st.sidebar:
    st.header("Spread Analysis Parameters")
    
    ticker_list_full = sorted([
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "JPM", "V", "JNJ", "LLY", "PEP",
        "BTC-USD", "ETH-USD", "ADA-USD", "SOL-USD", "DOT-USD", 
        "GC=F", "SI=F", "CL=F", "NG=F", "HG=F", "ZS=F", "ZC=F", "ZW=F",
        "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X",
        "OR.PA", "MC.PA", "AI.PA", "BNP.PA", "SAN.PA", "GLE.PA", "ACA.PA", "KER.PA", "RMS.PA",
        "ADS.DE", "ALV.DE", "BAS.DE", "BAYN.DE", "BMW.DE", "MBG.DE", "VOW3.DE", "SAP.DE", "SIE.DE",
        "BARC.L", "HSBA.L", "LLOY.L", "BP.L", "SHEL.L",
        "SPY", "QQQ", "DIA", "IWM", "EEM", "EFA", "AGG", "TLT", "GLD", "SLV"
    ])
    
    selected_ticker1 = st.selectbox("Select Ticker 1 (Independent Var for Beta)", ticker_list_full, index=ticker_list_full.index("AAPL"), key="spread_ticker1")
    selected_ticker2 = st.selectbox("Select Ticker 2 (Dependent Var for Beta)", ticker_list_full, index=ticker_list_full.index("MSFT"), key="spread_ticker2")
    
    start_date = st.date_input("Start Date", value=datetime(2023, 1, 1), key="spread_start_date")
    end_date = st.date_input("End Date", value=datetime.now().date(), key="spread_end_date")

    interval_options = {"Daily": "1d", "Hourly": "1h"} #, "Weekly": "1wk"}
    selected_interval_display = st.selectbox("Select Data Interval", list(interval_options.keys()), key="spread_interval_select")
    actual_interval = interval_options[selected_interval_display]

    st.markdown("--- ")
    st.markdown("**Strategy & Z-Score Parameters:**")
    rolling_window = st.slider("Z-Score Rolling Window (periods)", min_value=5, max_value=200, value=60, step=5, key="spread_rolling_window")
    z_upper_band = st.slider("Z-Score Upper Band (Enter Short)", min_value=0.5, max_value=3.0, value=1.5, step=0.1, key="spread_z_upper")
    z_lower_band = st.slider("Z-Score Lower Band (Enter Long)", min_value=-3.0, max_value=-0.5, value=-1.5, step=0.1, key="spread_z_lower")
    z_exit_band = st.slider("Z-Score Exit Band (Magnitude from Zero)", min_value=0.1, max_value=1.0, value=0.5, step=0.1, key="spread_z_exit")

    run_button = st.button("Calculate Spread & Run Backtest", key="spread_run_button", use_container_width=True)

if run_button:
    if selected_ticker1 == selected_ticker2:
        st.error("Error: Ticker 1 and Ticker 2 cannot be the same.")
    elif start_date >= end_date:
        st.error("Error: End date must be after start date.")
    else:
        st.subheader(f"Spread Analysis: {selected_ticker2} vs {selected_ticker1}")

        analysis_df, trades_df, error_message = calculate_price_spread_and_signals(
            selected_ticker1, selected_ticker2, 
            start_date, end_date, 
            window=rolling_window,
            upper_band=z_upper_band, 
            lower_band=z_lower_band, 
            exit_band=z_exit_band,
            interval=actual_interval
        )

        if error_message:
            st.error(error_message)
        
        if analysis_df is not None and not analysis_df.empty:
            fig, plot_error_message = create_spread_analysis_charts_plotly(
                analysis_df, selected_ticker1, selected_ticker2, 
                z_upper_band, z_lower_band, z_exit_band
            )
            if plot_error_message:
                st.warning(plot_error_message)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            
            if trades_df is not None and not trades_df.empty:
                st.markdown("--- ")
                st.subheader("Trade History & Performance")
                with st.expander("View List of Individual Trades", expanded=False):
                    st.dataframe(trades_df.style.format({
                        "Entry Spread Price": "{:.2f}", "Exit Spread Price": "{:.2f}",
                        "Entry Z-Score": "{:.2f}", "Exit Z-Score": "{:.2f}",
                        "Trade P&L": "{:.2f}"
                    }))

                st.markdown("<hr style='margin-top:1em; margin-bottom:1em;'>", unsafe_allow_html=True)
                st.markdown("<h4 style='text-align: center; margin-bottom:1em;'>Backtest Performance Summary</h4>", unsafe_allow_html=True)

                num_total_trades = len(trades_df)
                winning_trades_df = trades_df[trades_df['Trade P&L'] > 0]
                losing_trades_df = trades_df[trades_df['Trade P&L'] < 0]
                num_winning_trades = len(winning_trades_df)
                num_losing_trades = len(losing_trades_df)
                
                win_rate = (num_winning_trades / num_total_trades * 100) if num_total_trades > 0 else 0
                total_pnl = trades_df['Trade P&L'].sum() # Matches cumulative if all trades closed
                avg_pnl_per_trade = trades_df['Trade P&L'].mean() if num_total_trades > 0 else 0
                avg_winning_trade = winning_trades_df['Trade P&L'].mean() if num_winning_trades > 0 else 0
                avg_losing_trade = losing_trades_df['Trade P&L'].mean() if num_losing_trades > 0 else 0
                avg_win_loss_ratio = abs(avg_winning_trade / avg_losing_trade) if num_losing_trades > 0 and avg_losing_trade != 0 and avg_winning_trade !=0 else np.nan
                largest_win = winning_trades_df['Trade P&L'].max() if num_winning_trades > 0 else 0
                largest_loss = losing_trades_df['Trade P&L'].min() if num_losing_trades > 0 else 0

                def pnl_color_html(value):
                    color = "green" if value > 0 else "red" if value < 0 else "black"
                    return f'<span style="color: {color}; font-weight: bold;">{value:.2f}</span>'
                def win_rate_color_html(value):
                    color = "green" if value >= 50 else "red" if value < 40 else "orange"
                    return f'<span style="color: {color}; font-weight: bold;">{value:.2f}%</span>'
                def ratio_color_html(value):
                    if pd.isna(value):
                        return "N/A"
                    color = "green" if value > 1 else "red"
                    return f'<span style="color: {color}; font-weight: bold;">{value:.2f}</span>'

                st.markdown("**Overall Performance:**")
                col_overall1, col_overall2 = st.columns(2)
                col_overall1.markdown(f"Total Net P&L: {pnl_color_html(total_pnl)}", unsafe_allow_html=True)
                col_overall2.markdown(f"Win Rate: {win_rate_color_html(win_rate)}", unsafe_allow_html=True)
                
                st.markdown("<hr style='margin-top:0.5em; margin-bottom:0.5em;'>", unsafe_allow_html=True)
                st.markdown("**Per Trade Statistics:**")
                col_trade_stats1, col_trade_stats2, col_trade_stats3 = st.columns(3)
                col_trade_stats1.metric("Total Trades", num_total_trades)
                col_trade_stats2.markdown(f"Avg. P&L / Trade: {pnl_color_html(avg_pnl_per_trade)}", unsafe_allow_html=True)
                col_trade_stats3.markdown(f"Avg. Win/Loss Ratio: {ratio_color_html(avg_win_loss_ratio)}", unsafe_allow_html=True)
                
                st.markdown("<hr style='margin-top:0.5em; margin-bottom:0.5em;'>", unsafe_allow_html=True)
                st.markdown("**Winning Trades:**")
                col_win1, col_win2, col_win3 = st.columns(3)
                col_win1.metric("Wins", num_winning_trades)
                col_win2.markdown(f"Avg. Win: {pnl_color_html(avg_winning_trade)}", unsafe_allow_html=True)
                col_win3.markdown(f"Largest Win: {pnl_color_html(largest_win)}", unsafe_allow_html=True)
                
                st.markdown("<hr style='margin-top:0.5em; margin-bottom:0.5em;'>", unsafe_allow_html=True)
                st.markdown("**Losing Trades:**")
                col_loss1, col_loss2, col_loss3 = st.columns(3)
                col_loss1.metric("Losses", num_losing_trades)
                col_loss2.markdown(f"Avg. Loss: {pnl_color_html(avg_losing_trade)}", unsafe_allow_html=True)
                col_loss3.markdown(f"Largest Loss: {pnl_color_html(largest_loss)}", unsafe_allow_html=True)

            elif trades_df is not None and trades_df.empty:
                 st.info("No trades were executed based on the current strategy parameters.")
            elif analysis_df is not None: # analysis_df exists, but trades_df is None or empty
                st.warning("Spread analysis data generated, but trade backtest data could not be fully generated or no trades occurred.")
        elif not error_message: # Neither df nor error message means something unexpected
            st.info("Could not retrieve or process data for the spread analysis. Please check parameters.")
            
elif not run_button:
    st.info("Select assets and parameters in the sidebar, then click 'Calculate Spread & Run Backtest' to begin.")

st.caption("Disclaimer: Spread trading and statistical arbitrage involve risks. This tool is for educational purposes only and not financial advice.")
st.markdown("---")
st.markdown("Developed by **Yanis Montacer**")
st.markdown("Connect with me: [LinkedIn](https://www.linkedin.com/in/yanis-m-44418b288/) | [GitHub](https://github.com/YanisMtcr)")








