"""
Streamlit chat interface for the Stock Market AI Agent.
Features streaming responses, real-time status feedback, charts, and professional UI.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from agent import run_agent_with_streaming
from logging_config import setup_logging, metrics
from cache import price_cache, historical_cache

# Setup logging
setup_logging(level="INFO")

# Page config
st.set_page_config(
    page_title="Stock Market AI Agent",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for professional look
st.markdown("""
<style>
    /* Main theme */
    :root {
        --primary-color: #00D4AA;
        --secondary-color: #1E1E2E;
        --accent-color: #FF6B35;
        --success-color: #00D4AA;
        --danger-color: #FF4757;
        --warning-color: #FFA502;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #1E1E2E 0%, #2D2D44 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }

    .main-header h1 {
        color: #FFFFFF;
        font-size: 2rem;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .main-header p {
        color: #A0A0B0;
        margin: 0.5rem 0 0 0;
        font-size: 1rem;
    }

    /* Price cards */
    .price-card {
        background: linear-gradient(135deg, #FFFFFF 0%, #F8F9FA 100%);
        border-radius: 16px;
        padding: 1.25rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        border-left: 4px solid #00D4AA;
        margin: 0.75rem 0;
        transition: transform 0.2s ease;
    }

    .price-card:hover {
        transform: translateY(-2px);
    }

    .price-card.negative {
        border-left-color: #FF4757;
    }

    .price-card .symbol {
        font-size: 0.85rem;
        font-weight: 600;
        color: #6C757D;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .price-card .price {
        font-size: 1.75rem;
        font-weight: 700;
        color: #1E1E2E;
        margin: 0.25rem 0;
    }

    .price-card .change {
        font-size: 0.95rem;
        font-weight: 600;
        padding: 0.25rem 0.5rem;
        border-radius: 6px;
        display: inline-block;
    }

    .price-card .change.positive {
        background: rgba(0, 212, 170, 0.15);
        color: #00A884;
    }

    .price-card .change.negative {
        background: rgba(255, 71, 87, 0.15);
        color: #FF4757;
    }

    /* Metric cards */
    .metric-card {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }

    .metric-card .value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1E1E2E;
    }

    .metric-card .label {
        font-size: 0.75rem;
        color: #6C757D;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Comparison table */
    .comparison-header {
        background: linear-gradient(135deg, #1E1E2E 0%, #2D2D44 100%);
        color: white;
        padding: 1rem;
        border-radius: 12px 12px 0 0;
        margin-bottom: 0;
    }

    /* Chat messages */
    .stChatMessage {
        background: #FFFFFF;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }

    /* Status badges */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 0.35rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }

    .status-badge.running {
        background: rgba(255, 165, 2, 0.15);
        color: #CC8400;
    }

    .status-badge.success {
        background: rgba(0, 212, 170, 0.15);
        color: #00A884;
    }

    .status-badge.error {
        background: rgba(255, 71, 87, 0.15);
        color: #FF4757;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1E1E2E 0%, #2D2D44 100%);
    }

    section[data-testid="stSidebar"] .stMarkdown {
        color: #E0E0E0;
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #FFFFFF;
    }

    section[data-testid="stSidebar"] .stButton button {
        background: linear-gradient(135deg, #FF6B35 0%, #FF8F5A 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        width: 100%;
        transition: transform 0.2s ease;
    }

    section[data-testid="stSidebar"] .stButton button:hover {
        transform: scale(1.02);
    }

    /* Tool execution feedback */
    .tool-result {
        background: #F8F9FA;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        border-left: 3px solid #00D4AA;
        font-size: 0.9rem;
    }

    .tool-result.error {
        border-left-color: #FF4757;
        background: #FFF5F5;
    }

    /* Charts */
    .chart-container {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)


def render_header():
    """Render the main header."""
    st.markdown("""
    <div class="main-header">
        <h1>📈 Stock Market AI Agent</h1>
        <p>Real-time stock prices, crypto data, charts, and comparisons powered by AI</p>
    </div>
    """, unsafe_allow_html=True)


def render_price_card(symbol: str, price: float, change: float = None, currency: str = "USD"):
    """Render a styled price card."""
    change_class = "positive" if change and change >= 0 else "negative"
    card_class = "" if change is None or change >= 0 else "negative"

    change_html = ""
    if change is not None:
        arrow = "↑" if change >= 0 else "↓"
        change_html = f'<span class="change {change_class}">{arrow} {abs(change):.2f}%</span>'

    st.markdown(f"""
    <div class="price-card {card_class}">
        <div class="symbol">{symbol}</div>
        <div class="price">${price:,.2f} <small style="font-size: 0.7rem; color: #6C757D;">{currency}</small></div>
        {change_html}
    </div>
    """, unsafe_allow_html=True)


def render_chart(chart_data: dict):
    """Render a price chart from chart data."""
    if "error" in chart_data:
        st.error(chart_data["error"])
        return

    symbol = chart_data.get("symbol", "Unknown")
    dates = chart_data.get("dates", [])
    closes = chart_data.get("close", [])

    if not dates or not closes:
        st.warning("No chart data available")
        return

    # Create DataFrame for chart
    df = pd.DataFrame({
        "Date": pd.to_datetime(dates),
        "Price": closes
    })
    df.set_index("Date", inplace=True)

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1E1E2E 0%, #2D2D44 100%);
                color: white; padding: 0.75rem 1rem; border-radius: 12px 12px 0 0; margin-top: 1rem;">
        <span style="font-size: 1.1rem; font-weight: 600;">📊 {symbol} Price Chart</span>
        <span style="float: right; color: #A0A0B0; font-size: 0.85rem;">{chart_data.get('period', '1mo').upper()}</span>
    </div>
    """, unsafe_allow_html=True)

    st.line_chart(df, use_container_width=True)


def render_comparison(comparison_data: dict):
    """Render a stock comparison table."""
    if "error" in comparison_data:
        st.error(comparison_data["error"])
        return

    comparison = comparison_data.get("comparison", [])
    if not comparison:
        st.warning("No comparison data available")
        return

    st.markdown("""
    <div style="background: linear-gradient(135deg, #1E1E2E 0%, #2D2D44 100%);
                color: white; padding: 0.75rem 1rem; border-radius: 12px 12px 0 0; margin-top: 1rem;">
        <span style="font-size: 1.1rem; font-weight: 600;">📊 Stock Comparison</span>
    </div>
    """, unsafe_allow_html=True)

    # Create DataFrame
    df = pd.DataFrame(comparison)

    # Format columns
    if "market_cap" in df.columns:
        df["market_cap"] = df["market_cap"].apply(
            lambda x: f"${x/1e9:.1f}B" if x and x > 1e9 else (f"${x/1e6:.1f}M" if x else "N/A")
        )

    # Format change with color
    df["change_display"] = df["change_percent"].apply(
        lambda x: f"{'🟢' if x >= 0 else '🔴'} {x:+.2f}%"
    )

    # Rename columns for display
    display_df = df[["symbol", "name", "current_price", "change_display", "market_cap"]].copy()
    display_df.columns = ["Symbol", "Name", "Price ($)", "Change", "Market Cap"]

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Show best/worst
    col1, col2 = st.columns(2)
    with col1:
        st.success(f"🏆 **Best Performer:** {comparison_data.get('best_performer')}")
    with col2:
        st.error(f"📉 **Worst Performer:** {comparison_data.get('worst_performer')}")


def render_sidebar():
    """Render the sidebar with metrics and info."""
    with st.sidebar:
        # Logo/Title
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <span style="font-size: 3rem;">📈</span>
            <h2 style="margin: 0.5rem 0 0 0;">Stock Agent</h2>
            <p style="color: #A0A0B0; font-size: 0.85rem;">AI-Powered Market Data</p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Session Metrics
        st.markdown("### 📊 Session Metrics")

        metrics_data = metrics.get_summary()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Tool Calls", metrics_data["total_tool_calls"])
        with col2:
            st.metric("Cache Hit", f"{metrics_data['cache_hit_rate']}%")

        col3, col4 = st.columns(2)
        with col3:
            st.metric("Errors", metrics_data["total_errors"])
        with col4:
            avg_time = metrics_data["avg_response_time_ms"]
            st.metric("Avg Time", f"{avg_time:.0f}ms" if avg_time > 0 else "N/A")

        # Cache Status
        st.markdown("### 💾 Cache Status")
        st.caption(f"Price cache: {price_cache.size} items")
        st.caption(f"Historical cache: {historical_cache.size} items")

        st.divider()

        # Capabilities
        st.markdown("### ✨ Capabilities")
        st.markdown("""
        - 💰 **Real-time prices** for stocks & crypto
        - 📊 **Interactive charts** with historical data
        - 📈 **Price comparisons** side by side
        - 🔄 **Price changes** and percentages
        - 📅 **Average calculations** over periods
        - 🧮 **Math operations** for analysis
        """)

        st.divider()

        # Example prompts
        st.markdown("### 💡 Try asking")
        example_prompts = [
            "What's the current price of Tesla?",
            "Show me a chart of Bitcoin",
            "Compare Apple, Microsoft and Google",
            "What's NVDA's change vs yesterday?",
        ]

        for prompt in example_prompts:
            st.caption(f"• {prompt}")

        st.divider()

        # Clear button
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.conversation_history = []
            metrics.reset()
            st.rerun()

        # Footer
        st.markdown("""
        <div style="text-align: center; padding-top: 1rem; color: #6C757D; font-size: 0.75rem;">
            Built with Streamlit & OpenRouter<br>
            Data from Yahoo Finance
        </div>
        """, unsafe_allow_html=True)


# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

# Render sidebar
render_sidebar()

# Main content
render_header()

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # Render any associated charts
        if "chart_data" in message:
            render_chart(message["chart_data"])
        if "comparison_data" in message:
            render_comparison(message["comparison_data"])

# Chat input
if prompt := st.chat_input("Ask about stocks, crypto, or calculations..."):
    # Display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response with streaming
    with st.chat_message("assistant"):
        # Status container for showing what's happening
        status_container = st.status("🔍 Analyzing your question...", expanded=True)

        # Response placeholder for streaming text
        response_placeholder = st.empty()

        # Placeholders for charts and comparisons
        chart_placeholder = st.empty()
        comparison_placeholder = st.empty()

        try:
            full_response = ""
            tool_results = []
            chart_data = None
            comparison_data = None

            for item in run_agent_with_streaming(
                prompt,
                st.session_state.conversation_history
            ):
                if isinstance(item, dict):
                    if "status" in item:
                        # Update status
                        status_container.update(label=f"🔄 {item['status']}", state="running")

                    elif "tool_call" in item:
                        # Show tool execution
                        tool_name = item["tool_call"]
                        args = item["args"]
                        result = item["result"]

                        tool_results.append({
                            "name": tool_name,
                            "args": args,
                            "result": result
                        })

                        # Handle special tools
                        if tool_name == "get_chart_data" and "error" not in result:
                            chart_data = result
                            with chart_placeholder.container():
                                render_chart(result)

                        elif tool_name == "compare_stocks" and "error" not in result:
                            comparison_data = result
                            with comparison_placeholder.container():
                                render_comparison(result)

                        # Display tool info inside status
                        with status_container:
                            ticker = args.get("ticker", args.get("expression", ""))
                            if isinstance(ticker, list):
                                ticker = ", ".join(ticker[:3])
                            if args.get("tickers"):
                                ticker = ", ".join(args["tickers"][:3])

                            if "error" in result:
                                st.markdown(f"""
                                <div class="tool-result error">
                                    ❌ <strong>{tool_name}</strong>: {result['error']}
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                # Format result nicely with cards
                                if "price" in result and "percent_change" not in result:
                                    render_price_card(
                                        result.get('symbol', ticker),
                                        result['price'],
                                        currency=result.get('currency', 'USD')
                                    )
                                elif "percent_change" in result:
                                    render_price_card(
                                        result.get('symbol', ticker),
                                        result.get('current_price', result.get('price', 0)),
                                        change=result['percent_change'],
                                        currency=result.get('currency', 'USD')
                                    )
                                elif "average_price" in result:
                                    st.markdown(f"""
                                    <div class="tool-result">
                                        📊 <strong>{result.get('symbol', ticker)}</strong>
                                        {result['days']}-day average: <strong>${result['average_price']:,.2f}</strong>
                                    </div>
                                    """, unsafe_allow_html=True)
                                elif "result" in result:
                                    st.markdown(f"""
                                    <div class="tool-result">
                                        🧮 <strong>Calculation:</strong> {result['expression']} = <strong>{result['result']}</strong>
                                    </div>
                                    """, unsafe_allow_html=True)
                                elif "comparison" in result:
                                    st.markdown(f"""
                                    <div class="tool-result">
                                        📊 <strong>Compared {result['count']} stocks</strong> —
                                        Best: {result['best_performer']} | Worst: {result['worst_performer']}
                                    </div>
                                    """, unsafe_allow_html=True)
                                elif "dates" in result:
                                    st.markdown(f"""
                                    <div class="tool-result">
                                        📈 <strong>Chart ready</strong> for {result['symbol']} ({result['data_points']} data points)
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.json(result)

                    elif "done" in item:
                        # Update conversation history
                        st.session_state.conversation_history = item["history"]
                        status_container.update(label="✅ Complete", state="complete", expanded=False)

                else:
                    # Streaming text chunk
                    full_response += item
                    response_placeholder.markdown(full_response + "▌")

            # Final response without cursor
            response_placeholder.markdown(full_response)

            # Save to messages (include chart/comparison data for history)
            message_data = {
                "role": "assistant",
                "content": full_response
            }
            if chart_data:
                message_data["chart_data"] = chart_data
            if comparison_data:
                message_data["comparison_data"] = comparison_data

            st.session_state.messages.append(message_data)

        except ValueError as e:
            status_container.update(label="❌ Error", state="error")
            error_msg = str(e)
            st.error(f"⚠️ **Configuration Error:** {error_msg}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"⚠️ Configuration Error: {error_msg}"
            })
        except Exception as e:
            status_container.update(label="❌ Error", state="error")
            error_msg = str(e)
            st.error(f"⚠️ **Error:** {error_msg}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"⚠️ Error: {error_msg}"
            })
