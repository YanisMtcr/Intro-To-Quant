import streamlit as st 
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
import matplotlib.pyplot as plt 


def run_rsi_analysis_and_backtest(ticker, start_date, end_date, interval, rsi_window=14, rsi_oversold=30, rsi_overbought=70):
    data = yf.download(ticker, start=start_date, end=end_date, interval=interval, progress=False)
    if data.empty:
        return None, None, None 
        
    close_prices = data["Close"].squeeze() if isinstance(data["Close"], pd.DataFrame) else data["Close"]

    if close_prices.empty:
        return None, None, None

    rsi_indicator = RSIIndicator(close_prices, window=rsi_window)
    data["RSI"] = rsi_indicator.rsi()

    data["MA20"] = close_prices.rolling(window=20).mean()
    data["MA50"] = close_prices.rolling(window=50).mean()

    daily_analysis_df = pd.DataFrame(index=data.index)
    daily_analysis_df['price'] = close_prices
    daily_analysis_df['RSI'] = data['RSI']
    daily_analysis_df['signal'] = 0.0
    daily_analysis_df['daily_pnl'] = 0.0

    trades_list = []
    in_position = False
    entry_price = 0
    entry_date = None

    for i in range(len(data)):
        current_rsi = data['RSI'].iloc[i]
        current_price = close_prices.iloc[i]
        current_date = data.index[i]

        if pd.notna(current_rsi) and current_rsi < rsi_oversold and not in_position:
            in_position = True
            entry_price = current_price
            entry_date = current_date
            daily_analysis_df.loc[current_date, 'signal'] = 1.0
        
        elif pd.notna(current_rsi) and current_rsi > rsi_overbought and in_position:
            exit_price = current_price
            exit_date = current_date
            trade_pnl = exit_price - entry_price
            trades_list.append({
                'Ticker': ticker,
                'Trade Type': 'Long',
                'Entry Date': entry_date,
                'Entry Price': entry_price,
                'Entry RSI': data['RSI'].loc[entry_date] if entry_date in data.index and pd.notna(entry_date) else np.nan,
                'Exit Date': exit_date,
                'Exit Price': exit_price,
                'Exit RSI': current_rsi,
                'Trade P&L': trade_pnl,
                'Duration': exit_date - entry_date if pd.notna(entry_date) and pd.notna(exit_date) else pd.Timedelta(0)
            })
            if i > 0:
                 prev_day_price = close_prices.iloc[i-1]
                 daily_analysis_df.loc[current_date, 'daily_pnl'] = (exit_price - prev_day_price) 
            
            in_position = False
            entry_price = 0 
            entry_date = None
            daily_analysis_df.loc[current_date, 'signal'] = 0.0
        
        if in_position and daily_analysis_df.loc[current_date, 'signal'] == 0.0: 
             daily_analysis_df.loc[current_date, 'signal'] = 1.0

        if in_position:
            if i > 0 and daily_analysis_df.iloc[i-1]['signal'] == 1.0:
                 daily_analysis_df.loc[current_date, 'daily_pnl'] = current_price - close_prices.iloc[i-1]
            elif daily_analysis_df.iloc[i]['signal'] == 1.0 and (i==0 or daily_analysis_df.iloc[i-1]['signal']==0.0): 
                 daily_analysis_df.loc[current_date, 'daily_pnl'] = 0 
    
    if in_position:
        exit_price = close_prices.iloc[-1]
        exit_date = data.index[-1]
        trade_pnl = exit_price - entry_price
        trades_list.append({
            'Ticker': ticker,
            'Trade Type': 'Long',
            'Entry Date': entry_date,
            'Entry Price': entry_price,
            'Entry RSI': data['RSI'].loc[entry_date] if entry_date in data.index and pd.notna(entry_date) else np.nan,
            'Exit Date': exit_date,
            'Exit Price': exit_price,
            'Exit RSI': data['RSI'].iloc[-1],
            'Trade P&L': trade_pnl,
            'Duration': exit_date - entry_date if pd.notna(entry_date) and pd.notna(exit_date) else pd.Timedelta(0),
            'Status': 'Open at End'
        })
        if len(data) > 1 and daily_analysis_df.iloc[-2]['signal'] == 1.0:
             daily_analysis_df.loc[exit_date, 'daily_pnl'] = exit_price - close_prices.iloc[-2]

    trades_df = pd.DataFrame(trades_list)
    if not trades_df.empty:
        trades_df['Status'] = trades_df.get('Status', pd.Series(index=trades_df.index, dtype=str)).fillna('Closed')
        desired_cols = ['Ticker', 'Trade Type', 'Entry Date', 'Entry Price', 'Entry RSI', 'Exit Date', 'Exit Price', 'Exit RSI', 'Trade P&L', 'Duration', 'Status']
        trades_df = trades_df.reindex(columns=desired_cols)

    daily_analysis_df['cumulative_pnl'] = daily_analysis_df['daily_pnl'].cumsum()
    
    data_for_plot = data.copy()

    if 'signal' in daily_analysis_df.columns:
        shifted_signal = daily_analysis_df['signal'].shift(1).fillna(0)
        data_for_plot["Buy_Signal_Point"] = (data["RSI"] < rsi_oversold) & (shifted_signal == 0) & (daily_analysis_df['signal'] == 1.0)
        data_for_plot["Sell_Signal_Point"] = (data["RSI"] > rsi_overbought) & (shifted_signal == 1.0) & (daily_analysis_df['signal'] == 0.0)
    else: 
        data_for_plot["Buy_Signal_Point"] = False
        data_for_plot["Sell_Signal_Point"] = False

    return data_for_plot, trades_df, daily_analysis_df


def draw_rsi_chart_matplotlib(ticker, data_for_plot, rsi_oversold=30, rsi_overbought=70):
    if data_for_plot is None or data_for_plot.empty:
        return None 

    close_series = data_for_plot["Close"]
    ma20 = data_for_plot.get("MA20") 
    ma50 = data_for_plot.get("MA50")
    rsi_series = data_for_plot.get("RSI")

    fig, ax1 = plt.subplots(figsize=(14, 7))

    buy_points = data_for_plot[data_for_plot.get("Buy_Signal_Point", False)]
    sell_points = data_for_plot[data_for_plot.get("Sell_Signal_Point", False)]

    ax1.plot(data_for_plot.index, close_series, label="Close Price", color="#0072B2", linewidth=1.5)
    if ma20 is not None: ax1.plot(data_for_plot.index, ma20, label="MA20", color="#009E73", linestyle='--', linewidth=1.2)
    if ma50 is not None: ax1.plot(data_for_plot.index, ma50, label="MA50", color="#D55E00", linestyle=':', linewidth=1.2)
    ax1.set_xlabel("Date", fontsize=12)
    ax1.set_ylabel("Closing Price", fontsize=12)

    if not buy_points.empty:
        ax1.scatter(buy_points.index, buy_points["Close"], marker='^', color='#009E73', label=f'Buy Signal (RSI < {rsi_oversold})', s=100, alpha=0.9, edgecolors='w')
    if not sell_points.empty:
        ax1.scatter(sell_points.index, sell_points["Close"], marker='v', color='#D55E00', label=f'Sell Signal (RSI > {rsi_overbought})', s=100, alpha=0.9, edgecolors='w')
    
    ax1.tick_params(axis='x', rotation=30)
    ax1.grid(True, linestyle='--', alpha=0.7)

    ax2 = ax1.twinx()
    if rsi_series is not None and rsi_series.notnull().any():
        ax2.plot(data_for_plot.index, rsi_series, label="RSI", color="#CC79A7", alpha=0.65, linewidth=1.5)
        ax2.axhline(rsi_overbought, color='#D55E00', linestyle='--', linewidth=1, label=f'Overbought ({rsi_overbought})')
        ax2.axhline(rsi_oversold, color='#009E73', linestyle='--', linewidth=1, label=f'Oversold ({rsi_oversold})')
    ax2.set_ylabel("RSI Value", fontsize=12)
    ax2.set_ylim(0, 100)

    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = [], []
    if rsi_series is not None and rsi_series.notnull().any():
        lines_2, labels_2 = ax2.get_legend_handles_labels()
    
    ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc="upper left", fontsize=10)
    fig.suptitle(f"{ticker} - Price, Moving Averages & RSI Analysis", fontsize=16, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    return fig 


def draw_pnl_chart_matplotlib(daily_analysis_df):
    if daily_analysis_df is None or daily_analysis_df.empty or 'cumulative_pnl' not in daily_analysis_df.columns:
        return None 
    fig = plt.figure(figsize=(14, 4))
    plt.plot(daily_analysis_df.index, daily_analysis_df['cumulative_pnl'], label='Cumulative P&L', color='orange')
    plt.title('Backtest Cumulative P&L')
    plt.xlabel('Date')
    plt.ylabel('Cumulative P&L')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    return fig 