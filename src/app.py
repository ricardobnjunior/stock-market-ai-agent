"""
Streamlit chat interface for the Stock Market AI Agent.
Features streaming responses and real-time status feedback.
"""

import streamlit as st
from agent import run_agent_with_streaming


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

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

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

        try:
            full_response = ""
            tool_results = []

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

                        # Display tool info inside status
                        with status_container:
                            ticker = args.get("ticker", args.get("expression", ""))
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

            # Save to messages
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response
            })

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
    - **Price changes** and percentages
    - **Average calculations** over time periods
    - **Mathematical operations**

    **Example questions:**
    - "What's the current price of Tesla?"
    - "What was Bitcoin's price yesterday?"
    - "Calculate the average Apple stock price over the last week"
    - "What's the percentage change in NVDA compared to yesterday?"
    """)

    st.divider()

    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.session_state.conversation_history = []
        st.rerun()
