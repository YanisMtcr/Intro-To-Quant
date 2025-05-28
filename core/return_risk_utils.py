import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import norm
import plotly.graph_objects as go


def calculate_return_risk_metrics_and_plot(ticker, start_date, end_date, interval_code, interval_options_for_display_name):
    interval_display_name = [key for key, value in interval_options_for_display_name.items() if value == interval_code][0] if interval_options_for_display_name else interval_code

    try:
        data = yf.download(ticker, start=start_date, end=end_date, interval=interval_code, progress=False)
    except Exception as e: 
        return None, None, None, f"Error downloading data: {e}" 

    if data.empty:
        return None, None, None, f"No data found for {ticker} with interval {interval_display_name}."
    
    close_prices = data["Close"]
    if isinstance(close_prices, pd.DataFrame):
        close_prices = close_prices.squeeze()
    
    if close_prices.empty or len(close_prices) < 2:
        return None, None, None, f"Not enough closing price data ({len(close_prices)} points) for {ticker} to calculate returns."

    daily_returns = close_prices.pct_change() * 100 
    daily_returns = daily_returns.dropna() 

    if daily_returns.empty:
        return None, None, None, f"No valid return data for {ticker} after processing (all NaNs or empty)."

    mean_return = daily_returns.mean() 
    std_return = daily_returns.std()
    warning_message = None

    x_norm, y_norm = None, None
    if not (pd.isna(mean_return) or pd.isna(std_return) or std_return == 0 or std_return < 1e-6):
        try:
            x_norm = np.linspace(daily_returns.min(), daily_returns.max(), 500)
            y_norm = norm.pdf(x_norm, mean_return, std_return)
        except Exception as e:
            warning_message = f"Could not calculate normal distribution for {ticker} (mean: {mean_return:.2f}%, std: {std_return:.2f}%). Error: {e}"
            x_norm, y_norm = None, None 
    else:
        warning_message = f"Could not reliably calculate normal distribution for {ticker} (mean: {mean_return:.2f}%, std: {std_return:.2f}% - std might be zero or too small)."

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=daily_returns,
        name='Return Distribution',
        xbins=dict(size=(daily_returns.max() - daily_returns.min())/50 if (daily_returns.max() - daily_returns.min()) > 0 else 0.1), 
        marker_color='#1f77b4',
        opacity=0.7,
        histnorm='probability density'
    ))

    if x_norm is not None and y_norm is not None:
        fig.add_trace(go.Scatter(
            x=x_norm,
            y=y_norm,
            mode='lines',
            name='Normal Distribution Fit',
            line=dict(color='#ff7f0e', width=2)
        ))

    fig.update_layout(
        title_text=f"Return Distribution for {ticker} ({interval_display_name})", 
        xaxis_title_text="Return (%)",
        yaxis_title_text="Density",
        legend_title_text="Legend",
        bargap=0.01, 
        height=500 
    )
    
    return mean_return, std_return, fig, warning_message 