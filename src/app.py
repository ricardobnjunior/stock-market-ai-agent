"""
Streamlit chat interface for the Stock Market AI Agent.
Features streaming responses, real-time status feedback, and chart visualization.
"""

import streamlit as st
import pandas as pd
from agent import run_agent_with_streaming
from logging_config import setup_logging

# Setup logging
setup_logging(level="INFO")

st.set_page_config(
    page_title="Stock Market AI Agent",
    page_icon="📈",
    layout="centered",
)

st.title("📈 Stock Market AI Agent")
st.caption("Ask me about stock prices, crypto, and market data!")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

if "charts" not in st.session_state:
    st.session_state.charts = []


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

    st.subheader(f"📊 {symbol} Price Chart")
    st.line_chart(df)


def render_comparison(comparison_data: dict):
    """Render a stock comparison table."""
    if "error" in comparison_data:
        st.error(comparison_data["error"])
        return

    comparison = comparison_data.get("comparison", [])
    if not comparison:
        st.warning("No comparison data available")
        return

    # Create DataFrame
    df = pd.DataFrame(comparison)

    # Format columns
    if "market_cap" in df.columns:
        df["market_cap"] = df["market_cap"].apply(
            lambda x: f"${x/1e9:.1f}B" if x and x > 1e9 else (f"${x/1e6:.1f}M" if x else "N/A")
        )

    # Rename columns for display
    df = df.rename(columns={
        "symbol": "Symbol",
        "name": "Name",
        "current_price": "Current ($)",
        "yesterday_price": "Yesterday ($)",
        "change_percent": "Change (%)",
        "market_cap": "Market Cap"
    })

    st.subheader("📊 Stock Comparison")
    st.dataframe(df, use_container_width=True)

    # Show best/worst
    col1, col2 = st.columns(2)
    with col1:
        st.success(f"🏆 Best: **{comparison_data.get('best_performer')}**")
    with col2:
        st.error(f"📉 Worst: **{comparison_data.get('worst_performer')}**")


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
        status_container = st.status("Processing...", expanded=True)

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
                        status_container.update(label=item["status"], state="running")

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
                                st.error(f"**{tool_name}**({ticker}): {result['error']}")
                            else:
                                # Format result nicely
                                if "price" in result:
                                    st.success(f"**{result.get('symbol', ticker)}**: ${result['price']} {result.get('currency', 'USD')}")
                                elif "percent_change" in result:
                                    change = result['percent_change']
                                    emoji = "📈" if change >= 0 else "📉"
                                    st.success(f"**{result.get('symbol', ticker)}**: {change:+.2f}% {emoji}")
                                elif "average_price" in result:
                                    st.success(f"**{result.get('symbol', ticker)}** avg: ${result['average_price']}")
                                elif "result" in result:
                                    st.success(f"**Calculation**: {result['expression']} = {result['result']}")
                                elif "comparison" in result:
                                    st.success(f"**Compared {result['count']} stocks** - Best: {result['best_performer']}")
                                elif "dates" in result:
                                    st.success(f"**Chart data** for {result['symbol']} ({result['data_points']} points)")
                                else:
                                    st.json(result)

                    elif "done" in item:
                        # Update conversation history
                        st.session_state.conversation_history = item["history"]
                        status_container.update(label="Complete", state="complete", expanded=False)

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
            status_container.update(label="Error", state="error")
            error_msg = f"⚠️ Configuration Error: {str(e)}"
            st.error(error_msg)
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_msg
            })
        except Exception as e:
            status_container.update(label="Error", state="error")
            error_msg = f"⚠️ Error: {str(e)}"
            st.error(error_msg)
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_msg
            })

# Sidebar
with st.sidebar:
    st.header("About")
    st.markdown("""
    This AI agent can help you with:
    - **Current prices** for stocks and crypto
    - **Historical data** and trends
    - **Price charts** with visualization
    - **Stock comparisons** side by side
    - **Price changes** and percentages
    - **Average calculations** over time periods
    - **Mathematical operations**

    **Example questions:**
    - "What's the current price of Tesla?"
    - "What was Bitcoin's price yesterday?"
    - "Show me a chart of Apple for the last month"
    - "Compare Tesla, Apple and Microsoft"
    - "Calculate the average Apple stock price over the last week"
    - "What's the percentage change in NVDA compared to yesterday?"
    """)

    st.divider()

    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.session_state.conversation_history = []
        st.session_state.charts = []
        st.rerun()
