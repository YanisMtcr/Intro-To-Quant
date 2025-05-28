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
    from core.rsi_utils import run_rsi_analysis_and_backtest, draw_rsi_chart_matplotlib, draw_pnl_chart_matplotlib
except ImportError as e:
    st.error(f"Error importing from core.rsi_utils: {e}. \nEnsure the file exists in 'core' directory and 'core' has an __init__.py file. \nPYTHONPATH: {sys.path}")
    st.stop()

st.set_page_config(
    page_title="Interactive RSI Analyzer",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("RSI & Moving Average Financial Analyzer with Backtest")

st.markdown("""
This application provides an interactive platform for visualizing stock price trends, Moving Averages, and the Relative Strength Index (RSI). 
It also includes a simple backtest of an RSI-based trading strategy.

**Strategy Rules:**
*   **Enter Long:** Buy 1 share when RSI crosses below the \"Oversold\" level (default: 30) and not already in a position.
*   **Exit Long:** Sell the share when RSI crosses above the \"Overbought\" level (default: 70) and currently in a position.
*   No short selling is implemented in this version.

**Visualizations:**
1.  Price chart with Moving Averages, RSI, and actual Buy/Sell signals from the backtest.
2.  Cumulative P&L chart from the backtest.
3.  Table of individual trades and performance metrics.
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Analysis Parameters")
    
    ticker_list = sorted([
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "JPM", "V", "JNJ", 
        "BTC-USD", "ETH-USD", "GC=F", "SI=F", "CL=F", "EURUSD=X",
        "OR.PA", "MC.PA", "AI.PA", "BNP.PA", "SAN.PA", "GLE.PA", "ACA.PA"
    ])
    selected_ticker = st.selectbox("Choose Ticker", ticker_list, index=0, key="rsi_ticker_select")

    start_date = st.date_input("Start Date", value=datetime(2023, 1, 1), key="rsi_start_date")
    end_date = st.date_input("End Date", value=datetime.now().date(), key="rsi_end_date")
    
    if start_date >= end_date:
        st.error("Error: End date must be after start date.")
        st.stop()

    interval_options = {"Daily": "1d", "Hourly": "1h"}
    selected_interval_display = st.selectbox("Select Data Interval", list(interval_options.keys()), key="rsi_interval_select")
    actual_interval = interval_options[selected_interval_display]

    st.markdown("--- ")
    st.markdown("**RSI & Strategy Parameters:**")
    rsi_period = st.slider("RSI Period (days)", min_value=5, max_value=50, value=14, step=1, key="rsi_period_slider")
    rsi_oversold_level = st.slider("RSI Oversold Level (Buy Trigger)", min_value=10, max_value=40, value=30, step=1, key="rsi_oversold_slider")
    rsi_overbought_level = st.slider("RSI Overbought Level (Sell Trigger)", min_value=60, max_value=90, value=70, step=1, key="rsi_overbought_slider")

st.subheader(f"Analysis for: {selected_ticker}")
if selected_ticker:
    data_for_plot, trades_df, daily_analysis_df = run_rsi_analysis_and_backtest(
        selected_ticker, start_date, end_date, actual_interval, 
        rsi_window=rsi_period, rsi_oversold=rsi_oversold_level, rsi_overbought=rsi_overbought_level
    )

    if data_for_plot is None:
        st.error(f"Could not fetch or process data for {selected_ticker}. Please check parameters or try another ticker.")
    else:
        rsi_fig = draw_rsi_chart_matplotlib(selected_ticker, data_for_plot, rsi_oversold=rsi_oversold_level, rsi_overbought=rsi_overbought_level)
        if rsi_fig:
            st.pyplot(rsi_fig)
        else:
            st.warning("Could not generate RSI chart.")

        if trades_df is not None and daily_analysis_df is not None:
            st.markdown("--- ")
            st.subheader("Backtest Results")
            
            pnl_fig = draw_pnl_chart_matplotlib(daily_analysis_df)
            if pnl_fig:
                st.pyplot(pnl_fig)
            else:
                st.warning("Could not generate P&L chart.")
                
            st.markdown("<br>", unsafe_allow_html=True)

            with st.expander("View List of Individual Trades", expanded=False):
                if not trades_df.empty:
                    st.dataframe(trades_df.style.format({
                        "Entry Price": "{:.2f}", "Exit Price": "{:.2f}",
                        "Entry RSI": "{:.1f}", "Exit RSI": "{:.1f}",
                        "Trade P&L": "{:.2f}"
                    }))
                else:
                    st.info("No trades were executed based on the strategy and parameters.")
            
            if not trades_df.empty:
                st.markdown("<hr style='margin-top:1em; margin-bottom:1em;'>", unsafe_allow_html=True)
                st.markdown("<h4 style='text-align: center; margin-bottom:1em;'>Backtest Performance Summary</h4>", unsafe_allow_html=True)
                
                num_total_trades = len(trades_df)
                winning_trades_df = trades_df[trades_df['Trade P&L'] > 0]
                losing_trades_df = trades_df[trades_df['Trade P&L'] < 0]
                num_winning_trades = len(winning_trades_df)
                num_losing_trades = len(losing_trades_df)
                
                win_rate = (num_winning_trades / num_total_trades * 100) if num_total_trades > 0 else 0
                total_gross_pnl_trades = trades_df['Trade P&L'].sum()
                avg_pnl_per_trade = trades_df['Trade P&L'].mean() if num_total_trades > 0 else 0
                avg_winning_trade = winning_trades_df['Trade P&L'].mean() if num_winning_trades > 0 else 0
                avg_losing_trade = losing_trades_df['Trade P&L'].mean() if num_losing_trades > 0 else 0
                avg_win_loss_ratio = abs(avg_winning_trade / avg_losing_trade) if num_losing_trades > 0 and avg_losing_trade != 0 and avg_winning_trade !=0 else np.nan # added check for avg_winning_trade
                largest_win = winning_trades_df['Trade P&L'].max() if num_winning_trades > 0 else 0
                largest_loss = losing_trades_df['Trade P&L'].min() if num_losing_trades > 0 else 0

                def pnl_color(value): return "color: green;" if value > 0 else "color: red;" if value < 0 else "color: black;"
                def win_rate_color(value): return "color: green;" if value >= 50 else "color: red;" if value < 40 else "color: orange;"

                st.markdown("**Overall Performance:**")
                col_overall1, col_overall2 = st.columns(2)
                total_pnl_style = pnl_color(total_gross_pnl_trades)
                col_overall1.markdown(f"Total Net P&L: <span style='{total_pnl_style} font-weight: bold;'>{total_gross_pnl_trades:.2f}</span>", unsafe_allow_html=True)
                win_rate_style = win_rate_color(win_rate)
                col_overall2.markdown(f"Win Rate: <span style='{win_rate_style} font-weight: bold;'>{win_rate:.2f}%</span>", unsafe_allow_html=True)
                
                st.markdown("<hr style='margin-top:0.5em; margin-bottom:0.5em;'>", unsafe_allow_html=True)
                st.markdown("**Per Trade Statistics:**")
                col_trade_stats1, col_trade_stats2, col_trade_stats3 = st.columns(3)
                col_trade_stats1.metric("Total Trades", num_total_trades)
                avg_pnl_style = pnl_color(avg_pnl_per_trade)
                col_trade_stats2.markdown(f"Avg. P&L / Trade: <span style='{avg_pnl_style}'>{avg_pnl_per_trade:.2f}</span>", unsafe_allow_html=True)
                ratio_style = "color: green;" if pd.notna(avg_win_loss_ratio) and avg_win_loss_ratio > 1 else ("color: red;" if pd.notna(avg_win_loss_ratio) else "color: black;")
                col_trade_stats3.markdown(f"Avg. Win/Loss Ratio: <span style='{ratio_style}'>{avg_win_loss_ratio:.2f}</span>" if pd.notna(avg_win_loss_ratio) else "Avg. Win/Loss Ratio: N/A", unsafe_allow_html=True)
                
                st.markdown("<hr style='margin-top:0.5em; margin-bottom:0.5em;'>", unsafe_allow_html=True)
                st.markdown("**Winning Trades:**")
                col_win1, col_win2, col_win3 = st.columns(3)
                col_win1.metric("Wins", num_winning_trades)
                avg_win_style = pnl_color(avg_winning_trade)
                col_win2.markdown(f"Avg. Win: <span style='{avg_win_style}'>{avg_winning_trade:.2f}</span>", unsafe_allow_html=True)
                largest_win_style = pnl_color(largest_win)
                col_win3.markdown(f"Largest Win: <span style='{largest_win_style}'>{largest_win:.2f}</span>", unsafe_allow_html=True)
                
                st.markdown("<hr style='margin-top:0.5em; margin-bottom:0.5em;'>", unsafe_allow_html=True)
                st.markdown("**Losing Trades:**")
                col_loss1, col_loss2, col_loss3 = st.columns(3)
                col_loss1.metric("Losses", num_losing_trades)
                avg_loss_style = pnl_color(avg_losing_trade)
                col_loss2.markdown(f"Avg. Loss: <span style='{avg_loss_style}'>{avg_losing_trade:.2f}</span>", unsafe_allow_html=True)
                largest_loss_style = pnl_color(largest_loss)
                col_loss3.markdown(f"Largest Loss: <span style='{largest_loss_style}'>{largest_loss:.2f}</span>", unsafe_allow_html=True)
            elif trades_df is not None and trades_df.empty:
                 st.info("No trades were executed based on the current strategy parameters.")
        elif data_for_plot is not None: 
            st.warning("Backtest data could not be fully generated, so performance metrics are unavailable.")

else:
    st.info("Please select a ticker and configure parameters in the sidebar to begin analysis.")

st.caption("Disclaimer: This tool is for educational and illustrative purposes only. Not financial advice.")
st.markdown("---")
st.markdown("Developed by **Yanis Montacer**")
st.markdown("Connect with me: [LinkedIn](https://www.linkedin.com/in/yanis-m-44418b288/) | [GitHub](https://github.com/YanisMtcr)")