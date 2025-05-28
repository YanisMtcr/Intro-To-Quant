import yfinance as yf
import pandas as pd
import plotly.graph_objects as go


def generate_correlation_heatmap_plotly(tickers_list, start_date, end_date, interval):

    if not tickers_list:
        return None, "Please select at least two tickers."
    if len(tickers_list) < 2:
        return None, f"Correlation matrix requires at least two tickers. You selected {len(tickers_list)}."
        
    try:
        data = yf.download(tickers_list, start=start_date, end=end_date, interval=interval, progress=False)
    except Exception as e:
        return None, f"An error occurred during data download: {e}"
        
    if data.empty:
        return None, f"No data downloaded for the selected tickers/period: {', '.join(tickers_list)}."

    close_prices = None
    if isinstance(data.columns, pd.MultiIndex):
        if 'Close' in data.columns.levels[0]:
            close_prices = data['Close']
        else:
            return None, "Could not find 'Close' prices in the downloaded multi-ticker data."
    elif 'Close' in data.columns: 

        if isinstance(data['Close'], pd.Series):
            close_prices = data[['Close']]
        else: 
            close_prices = data['Close']
    else:
        return None, "Downloaded data format not recognized or 'Close' column is missing."

    if close_prices is None or close_prices.empty:
        return None, "Closing price data is empty after attempting to extract it."
        

    close_prices = close_prices.dropna(axis=1, how='all') 

    close_prices = close_prices.dropna(axis=0, how='any') 

    if close_prices.shape[1] < 2:
        return None, f"Not enough tickers with valid, overlapping data to compute a correlation matrix (requires at least two). Found: {close_prices.shape[1]} after cleaning. Tickers: {', '.join(close_prices.columns.tolist())}"
        
    try:
        corr_matrix = close_prices.corr()
    except Exception as e:
        return None, f"Error computing correlation matrix: {e}. This can happen with non-numeric data or insufficient overlap."
        
    if corr_matrix.empty or corr_matrix.shape[0] < 2 or corr_matrix.shape[1] < 2:
        return None, "Could not compute a valid correlation matrix. Ensure there is sufficient overlapping data for the selected tickers."

    annot_text = corr_matrix.map(lambda x: f'{x:.2f}').values

    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns.tolist(),
        y=corr_matrix.index.tolist(),
        colorscale='RdBu',
        zmin=-1, 
        zmax=1,
        text=annot_text,
        texttemplate="%{text}",
        hoverongaps=False,
        xgap=1, 
        ygap=1
    ))

    fig.update_layout(
        title_text='Correlation Matrix of Closing Prices',
        xaxis_title="Tickers",
        yaxis_title="Tickers",
        height=max(450, len(corr_matrix.columns) * 45 + 150),
        width=max(550, len(corr_matrix.columns) * 55 + 150),
        xaxis_showgrid=False,
        yaxis_showgrid=False,
        yaxis_autorange='reversed',
        margin=dict(l=100, r=50, t=100, b=100)
    )
    return fig, None 