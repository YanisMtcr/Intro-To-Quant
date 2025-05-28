import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime # Keep for potential use, though not directly in these functions now
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def Correlation_data(ticker1 , ticker2 , start_date , end_date , interval):
    data = yf.download([ticker1, ticker2], start=start_date, end=end_date, interval=interval, progress=False)
    if data.empty or not isinstance(data.columns, pd.MultiIndex) or len(data.columns.levels) < 2:
        # st.warning(f"Could not download sufficient data for {ticker1} and {ticker2}. Check tickers or period.")
        return pd.DataFrame() # Return empty DataFrame if download fails or format is unexpected
        
    close_prices1 = data.get(('Close', ticker1))
    close_prices2 = data.get(('Close', ticker2))

    if close_prices1 is None or close_prices2 is None:
        # st.warning(f"Could not extract closing prices for one or both tickers: {ticker1}, {ticker2}.")
        return pd.DataFrame()
    
    df = pd.concat([close_prices1, close_prices2], axis=1, join='inner')
    df.columns = [ticker1, ticker2]
    return df.dropna() # Drop rows with NaNs that result from non-overlapping dates


def calculate_correlation(df, window=50, std_dev=1, wide_window=200):
    if df.empty or len(df.columns) < 2:
        # st.warning("Input DataFrame for correlation calculation is empty or has too few columns.")
        return pd.DataFrame()
        
    ticker1 = df.columns[0]
    ticker2 = df.columns[1]
    
    # Ensure there are enough non-NaN values for the rolling window
    if df[ticker1].notna().sum() < window or df[ticker2].notna().sum() < window:
        # st.warning(f"Not enough data points for one or both tickers for the rolling window of {window}. T1: {df[ticker1].notna().sum()}, T2: {df[ticker2].notna().sum()}")
        return pd.DataFrame()

    df_corr = pd.DataFrame(index=df.index)
    df_corr["rolling_correlation"] = df[ticker1].rolling(window=window).corr(df[ticker2])
    
    # For avg_correlation and std_correlation, use expanding mean/std if not enough data for wide_window
    if df_corr["rolling_correlation"].notna().sum() < wide_window:
        df_corr["avg_correlation"] = df_corr["rolling_correlation"].expanding(min_periods=1).mean()
        df_corr["std_correlation"] = df_corr["rolling_correlation"].expanding(min_periods=1).std()
    else:
        df_corr["avg_correlation"] = df_corr["rolling_correlation"].rolling(window=wide_window).mean()
        df_corr["std_correlation"] = df_corr["rolling_correlation"].rolling(window=wide_window).std()

    df_corr["upper_band"] = df_corr["avg_correlation"] + std_dev * df_corr["std_correlation"]
    df_corr["lower_band"] = df_corr["avg_correlation"] - std_dev * df_corr["std_correlation"]
    
    # Signal logic (remains part of calculation as it's based on calculated values)
    df_corr["signal"] = 0 # Default to no signal
    # Ensure indices align and we are not operating on NaN slices from rolling operations
    df_corr.loc[df_corr["rolling_correlation"].notna() & (df_corr["rolling_correlation"] > df_corr["upper_band"]), "signal"] = -1 # High correlation
    df_corr.loc[df_corr["rolling_correlation"].notna() & (df_corr["rolling_correlation"] < df_corr["lower_band"]), "signal"] = 1  # Low correlation (changed from 2 to 1 for clarity)
    
    # Drop rows where rolling_correlation is NaN, as other metrics depend on it
    return df_corr[["rolling_correlation", "avg_correlation", "upper_band", "lower_band", "signal"]].dropna(subset=['rolling_correlation'])


def plot_combined_correlation_plotly(price_df, corr_df):
    if price_df.empty or corr_df.empty or len(price_df.columns) < 2:
        # st.warning("Cannot plot: Price or Correlation DataFrame is empty or insufficient.")
        return go.Figure() # Return an empty figure if data is insufficient

    ticker1 = price_df.columns[0]
    ticker2 = price_df.columns[1]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Price series
    fig.add_trace(go.Scatter(x=price_df.index, y=price_df[ticker1], name=f'{ticker1} Price', line=dict(color='#1f77b4')), secondary_y=False)
    fig.add_trace(go.Scatter(x=price_df.index, y=price_df[ticker2], name=f'{ticker2} Price', line=dict(color='#ff7f0e')), secondary_y=False)

    # Correlation series
    fig.add_trace(go.Scatter(x=corr_df.index, y=corr_df['rolling_correlation'], name='Rolling Correlation', line=dict(color='#2ca02c')), secondary_y=True)
    fig.add_trace(go.Scatter(x=corr_df.index, y=corr_df['avg_correlation'], name='Avg Correlation', line=dict(color='#d62728', dash='dash')), secondary_y=True)
    
    # Correlation bands
    fig.add_trace(go.Scatter(x=corr_df.index, y=corr_df['upper_band'], name='Upper Band', line=dict(width=0), showlegend=False), secondary_y=True)
    # Fill area between upper and lower bands for visual clarity
    fig.add_trace(go.Scatter(
        x=corr_df.index, 
        y=corr_df['lower_band'], 
        name='Correlation Bands', # Single legend entry for the band area
        line=dict(width=0), 
        fill='tonexty', # Fill to the previous trace (upper_band)
        fillcolor='rgba(148, 103, 189, 0.2)', # A light purple color
        showlegend=True, 
        legendgroup="bands", 
        legendgrouptitle_text="Corr. Bands"
    ), secondary_y=True)

    # Signals on correlation plot
    # Ensure signals are only plotted where they exist
    low_corr_signals = corr_df[corr_df['signal'] == 1] # Changed from 2 to 1
    high_corr_signals = corr_df[corr_df['signal'] == -1]
    
    if not low_corr_signals.empty:
        fig.add_trace(go.Scatter(x=low_corr_signals.index, y=low_corr_signals['rolling_correlation'], mode='markers', name='Low Corr Signal (Enter)', marker=dict(color='#2ca02c', symbol='triangle-up', size=8)), secondary_y=True)
    if not high_corr_signals.empty:
        fig.add_trace(go.Scatter(x=high_corr_signals.index, y=high_corr_signals['rolling_correlation'], mode='markers', name='High Corr Signal (Exit/Revert)', marker=dict(color='#d62728', symbol='triangle-down', size=8)), secondary_y=True)

    fig.update_layout(
        title_text=f"Price & Rolling Correlation Analysis: {ticker1} / {ticker2}",
        height=600,
        legend_title_text='Legend',
        hovermode='x unified',
        yaxis_title_text="Price",
        yaxis2_title_text="Correlation"
    )
    # Explicitly set ranges if desired, e.g., for correlation y-axis
    fig.update_yaxes(title_text="Price", secondary_y=False)
    fig.update_yaxes(title_text="Correlation", secondary_y=True, range=[-1.1, 1.1]) # Ensure y-axis for correlation is clear
    
    return fig 