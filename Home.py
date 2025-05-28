import streamlit as st

st.set_page_config(
    page_title="Quantitative Finance Hub",
    page_icon=":chart_with_upwards_trend:",
    layout="wide"
)

st.title("Intro to Quantitative Finance – Interactive Tools")
st.write(
    """
    **Welcome to the Quantitative Finance Hub!**

    This is a collection of interactive tools designed for quantitative financial analysis, built with Python and Streamlit.
    Explore the modules for:
    *   **Interactive RSI Analyzer**: Technical analysis with RSI, moving averages, and a simple backtesting feature.
    *   **Return and Risk Analyzer**: Visualize return distributions and key risk metrics.
    *   **Correlation Matrix Analyzer**: Compute and display correlation matrices for multiple assets.
    *   **Rolling Correlation Analyzer**: Analyze dynamic rolling correlations between two assets.
    *   **Interactive Spread Analysis**: Perform pairs trading spread analysis with z-score signals and backtesting.

    Use the sidebar to navigate between the different analysis tools.
    """
)
st.caption("Disclaimer: All tools are for educational and illustrative purposes only. Not financial advice.")

st.markdown("---")
st.markdown("Developed by **Yanis Montacer**")
st.markdown("Connect with me: [LinkedIn](https://www.linkedin.com/in/yanis-m-44418b288/) | [GitHub](https://github.com/YanisMtcr)")

