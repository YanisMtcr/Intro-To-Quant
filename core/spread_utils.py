import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.linear_model import LinearRegression
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def calculate_price_spread_and_signals(
    ticker1, ticker2, start_date, end_date, window=60,
    upper_band=1.5, lower_band=-1.5, exit_band=0.5, interval="1d"
):
    error_message = None
    data1_raw = yf.download(ticker1, start=start_date, end=end_date, interval=interval, progress=False)
    data2_raw = yf.download(ticker2, start=start_date, end=end_date, interval=interval, progress=False)

    if data1_raw.empty or data2_raw.empty:
        error_message = f"No price data for {ticker1} or {ticker2} in the selected period with interval {interval}."
        return pd.DataFrame(), pd.DataFrame(), error_message

    prices_df = pd.concat([data1_raw['Close'], data2_raw['Close']], axis=1).dropna()
    prices_df.columns = [ticker1, ticker2]

    if len(prices_df) < window or len(prices_df) < 2:
        error_message = f"Not enough data points ({len(prices_df)}) for analysis after aligning prices. Min required: {max(2, window)}."
        return pd.DataFrame(), pd.DataFrame(), error_message

    x_prices = prices_df[ticker1].values.reshape(-1, 1)
    y_prices = prices_df[ticker2].values.reshape(-1, 1)
    
    try:
        model_prices = LinearRegression().fit(x_prices, y_prices)
    except ValueError as e:
        error_message = f"Linear regression failed. Ensure data is numeric and not all NaNs. Error: {e}"
        return pd.DataFrame(), pd.DataFrame(), error_message
        
    beta = model_prices.coef_[0][0]
    
    analysis_df = pd.DataFrame(index=prices_df.index)
    analysis_df['spread'] = prices_df[ticker2] - beta * prices_df[ticker1]
    analysis_df[ticker1] = prices_df[ticker1]
    analysis_df[ticker2] = prices_df[ticker2]

    analysis_df['rolling_mean_spread'] = analysis_df['spread'].rolling(window=window).mean()
    analysis_df['rolling_std_spread'] = analysis_df['spread'].rolling(window=window).std()
    
    analysis_df['z_score'] = (analysis_df['spread'] - analysis_df['rolling_mean_spread']) / analysis_df['rolling_std_spread']
    analysis_df['z_score'].replace([np.inf, -np.inf], np.nan, inplace=True) 

    analysis_df["signal"] = 0.0
    entry_short_condition = analysis_df['z_score'] > upper_band
    entry_long_condition = analysis_df['z_score'] < lower_band
    exit_condition = pd.Series(False, index=analysis_df.index)
    valid_zscore_for_exit = analysis_df['z_score'].notna()
    if valid_zscore_for_exit.any(): 
        exit_condition[valid_zscore_for_exit] = analysis_df['z_score'][valid_zscore_for_exit].abs() < exit_band

    current_position = 0.0
    signals_generated = []
    for i in range(len(analysis_df)):
        if pd.isna(analysis_df['z_score'].iloc[i]):
            signals_generated.append(current_position)
            continue
        is_entry_short = entry_short_condition.iloc[i]
        is_entry_long = entry_long_condition.iloc[i]
        is_exit = exit_condition.iloc[i]
        if current_position == 0:
            if is_entry_long: current_position = 1.0
            elif is_entry_short: current_position = -1.0
        elif current_position == 1.0:
            if is_exit: current_position = 0.0
            elif is_entry_short: current_position = -1.0
        elif current_position == -1.0:
            if is_exit: current_position = 0.0
            elif is_entry_long: current_position = 1.0
        signals_generated.append(current_position)
    analysis_df['signal'] = signals_generated

    analysis_df['prev_spread'] = analysis_df['spread'].shift(1)
    analysis_df['pos_held_during_period'] = analysis_df['signal'].shift(1).fillna(0)
    analysis_df['spread_change'] = analysis_df['spread'] - analysis_df['prev_spread']
    analysis_df['daily_pnl'] = analysis_df['spread_change'] * analysis_df['pos_held_during_period']
    analysis_df['daily_pnl'].fillna(0, inplace=True)
    analysis_df['cumulative_pnl'] = analysis_df['daily_pnl'].cumsum()

    trades_list = []
    current_trade = {}
    position_active = False
    analysis_df['prev_signal_marker'] = analysis_df['signal'].shift(1).fillna(0)

    for i in range(len(analysis_df)):
        current_signal = analysis_df['signal'].iloc[i]
        prev_signal = analysis_df['prev_signal_marker'].iloc[i]
        current_date = analysis_df.index[i]
        current_spread_price = analysis_df['spread'].iloc[i]
        current_zscore = analysis_df['z_score'].iloc[i]

        if not position_active and (current_signal == 1.0 or current_signal == -1.0):
            position_active = True
            current_trade = {
                'Ticker1': ticker1, 'Ticker2': ticker2,
                'Trade Type': 'Long Spread' if current_signal == 1.0 else 'Short Spread',
                'Entry Date': current_date, 'Entry Spread Price': current_spread_price,
                'Entry Z-Score': current_zscore, 'Direction': current_signal
            }
        elif position_active and current_signal == 0.0:
            position_active = False
            current_trade['Exit Date'] = current_date
            current_trade['Exit Spread Price'] = current_spread_price
            current_trade['Exit Z-Score'] = current_zscore
            pnl = (current_trade['Exit Spread Price'] - current_trade['Entry Spread Price']) * current_trade['Direction']
            current_trade['Trade P&L'] = pnl
            current_trade['Duration'] = current_trade['Exit Date'] - current_trade['Entry Date']
            trades_list.append(current_trade)
            current_trade = {}
        elif position_active and current_signal != prev_signal and prev_signal != 0:
            current_trade['Exit Date'] = current_date
            current_trade['Exit Spread Price'] = current_spread_price
            current_trade['Exit Z-Score'] = current_zscore
            pnl = (current_trade['Exit Spread Price'] - current_trade['Entry Spread Price']) * current_trade['Direction']
            current_trade['Trade P&L'] = pnl
            current_trade['Duration'] = current_trade['Exit Date'] - current_trade['Entry Date']
            trades_list.append(current_trade)
            current_trade = {
                'Ticker1': ticker1, 'Ticker2': ticker2,
                'Trade Type': 'Long Spread' if current_signal == 1.0 else 'Short Spread',
                'Entry Date': current_date, 'Entry Spread Price': current_spread_price,
                'Entry Z-Score': current_zscore, 'Direction': current_signal
            }
            
    if position_active and current_trade:
        current_trade['Exit Date'] = analysis_df.index[-1]
        current_trade['Exit Spread Price'] = analysis_df['spread'].iloc[-1]
        current_trade['Exit Z-Score'] = analysis_df['z_score'].iloc[-1]
        pnl = (current_trade['Exit Spread Price'] - current_trade['Entry Spread Price']) * current_trade['Direction']
        current_trade['Trade P&L'] = pnl
        current_trade['Duration'] = current_trade['Exit Date'] - current_trade['Entry Date']
        current_trade['Status'] = 'Open at End'
        trades_list.append(current_trade)

    trades_df = pd.DataFrame(trades_list)
    if not trades_df.empty:
        if 'Status' not in trades_df.columns: trades_df['Status'] = 'Closed'
        else: trades_df['Status'].fillna('Closed', inplace=True)
        desired_columns = [
            'Ticker1', 'Ticker2', 'Trade Type', 'Entry Date', 'Entry Spread Price',
            'Entry Z-Score', 'Exit Date', 'Exit Spread Price', 'Exit Z-Score', 
            'Direction', 'Trade P&L', 'Duration', 'Status'
        ]
        trades_df = trades_df.reindex(columns=desired_columns)
        trades_df['Status'].fillna('Closed', inplace=True)

    analysis_df.drop(columns=['prev_spread', 'pos_held_during_period', 'spread_change', 'prev_signal_marker'], inplace=True, errors='ignore')
    return analysis_df, trades_df, error_message

def create_spread_analysis_charts_plotly(df, ticker1, ticker2, upper_band, lower_band, exit_band):
    if df is None or df.empty:
        return go.Figure(), "Input DataFrame for plotting is empty or None."
    
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        subplot_titles=(f'Price Spread: {ticker2} - Beta*{ticker1}', 
                                        'Z-Score & Trading Signals', 
                                        'Cumulative Profit & Loss (P&L)'),
                        vertical_spacing=0.08, row_heights=[0.38, 0.38, 0.24])

    if 'prev_signal' not in df.columns:
        df['prev_signal'] = df['signal'].shift(1).fillna(0)

    fig.add_trace(go.Scatter(x=df.index, y=df['spread'], mode='lines', name='Price Spread', legendgroup='1'), row=1, col=1)
    if 'rolling_mean_spread' in df.columns: 
        fig.add_trace(go.Scatter(x=df.index, y=df['rolling_mean_spread'], mode='lines', name='Rolling Mean', line=dict(dash='dot'), legendgroup='1'), row=1, col=1)

    if 'z_score' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['z_score'], mode='lines', name='Z-Score', legendgroup='2'), row=2, col=1)
        fig.add_hline(y=upper_band, line_dash="dash", line_color="red", annotation_text=f"Upper ({upper_band:.2f})", row=2, col=1)
        fig.add_hline(y=lower_band, line_dash="dash", line_color="green", annotation_text=f"Lower ({lower_band:.2f})", row=2, col=1)
        fig.add_hline(y=exit_band, line_dash="dot", line_color="blue", annotation_text=f"Exit ({exit_band:.2f})", row=2, col=1)
        fig.add_hline(y=-exit_band, line_dash="dot", line_color="blue", annotation_text=f"Exit (-{exit_band:.2f})", row=2, col=1)
        fig.add_hline(y=0, line_dash="solid", line_color="black", row=2, col=1, annotation_text="Z=0")

        entry_long_markers = df[(df['signal'] == 1.0) & (df['prev_signal'] != 1.0)]
        entry_short_markers = df[(df['signal'] == -1.0) & (df['prev_signal'] != -1.0)]
        exit_long_markers = df[(df['signal'] == 0.0) & (df['prev_signal'] == 1.0)]
        exit_short_markers = df[(df['signal'] == 0.0) & (df['prev_signal'] == -1.0)]

        if not entry_long_markers.empty: fig.add_trace(go.Scatter(x=entry_long_markers.index, y=entry_long_markers['z_score'], mode='markers', name='Enter Long', marker=dict(color='green', size=10, symbol='triangle-up'), legendgroup='2'), row=2, col=1)
        if not entry_short_markers.empty: fig.add_trace(go.Scatter(x=entry_short_markers.index, y=entry_short_markers['z_score'], mode='markers', name='Enter Short', marker=dict(color='red', size=10, symbol='triangle-down'), legendgroup='2'), row=2, col=1)
        if not exit_long_markers.empty: fig.add_trace(go.Scatter(x=exit_long_markers.index, y=exit_long_markers['z_score'], mode='markers', name='Exit Long', marker=dict(color='blue', size=8, symbol='x'), legendgroup='2'), row=2, col=1)
        if not exit_short_markers.empty: fig.add_trace(go.Scatter(x=exit_short_markers.index, y=exit_short_markers['z_score'], mode='markers', name='Exit Short', marker=dict(color='purple', size=8, symbol='x'), legendgroup='2'), row=2, col=1)
        
        if not entry_long_markers.empty: fig.add_trace(go.Scatter(x=entry_long_markers.index, y=entry_long_markers['spread'], mode='markers', marker=dict(color='green', size=10, symbol='triangle-up', opacity=0.7), showlegend=False, legendgroup='1'), row=1, col=1)
        if not entry_short_markers.empty: fig.add_trace(go.Scatter(x=entry_short_markers.index, y=entry_short_markers['spread'], mode='markers', marker=dict(color='red', size=10, symbol='triangle-down', opacity=0.7), showlegend=False, legendgroup='1'), row=1, col=1)
        if not exit_long_markers.empty: fig.add_trace(go.Scatter(x=exit_long_markers.index, y=exit_long_markers['spread'], mode='markers', marker=dict(color='blue', size=8, symbol='x', opacity=0.7), showlegend=False, legendgroup='1'), row=1, col=1)
        if not exit_short_markers.empty: fig.add_trace(go.Scatter(x=exit_short_markers.index, y=exit_short_markers['spread'], mode='markers', marker=dict(color='purple', size=8, symbol='x', opacity=0.7), showlegend=False, legendgroup='1'), row=1, col=1)

    if 'cumulative_pnl' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['cumulative_pnl'], mode='lines', name='Cumulative P&L', line=dict(color='orange'), legendgroup='3'), row=3, col=1)
        fig.add_hline(y=0, line_dash="dash", line_color="grey", row=3, col=1)

    fig.update_layout(
        height=1100,
        legend=dict(tracegroupgap=10),
        title_text=f'Spread Analysis & P&L: {ticker1} vs {ticker2}',
        hovermode='x unified'
    )
    fig.update_xaxes(title_text="Date", row=3, col=1)
    fig.update_yaxes(title_text="Price Spread Value", row=1, col=1)
    fig.update_yaxes(title_text="Z-Score Value", row=2, col=1)
    fig.update_yaxes(title_text="Cumulative P&L", row=3, col=1)
    
    return fig, None 