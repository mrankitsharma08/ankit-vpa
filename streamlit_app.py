import streamlit as st
import pandas as pd
import plotly.express as px

# UI Configuration
st.set_page_config(page_title="TPV Analyzer Pro", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for a cleaner look
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_index=True)

st.title("📊 TPV Market Share Analyzer")
st.markdown("---")

# Sidebar for Setup & Inputs
with st.sidebar:
    st.header("1. Data Source")
    uploaded_file = st.file_uploader("Upload Marketshare CSV", type="csv")
    
    st.header("2. Analysis Filters")
    raw_input = st.text_input("Receiver Names", "Amazon, Flipkart, Myntra")
    st.caption("Separate names with commas")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine='python')
        
        # Data Processing
        receiver_list = [name.strip().lower() for name in raw_input.split(',')]
        df['receiver_name_lower'] = df['receiver_name'].astype(str).str.lower()
        filtered_df = df[df['receiver_name_lower'].isin(receiver_list)].copy()

        if not filtered_df.empty:
            # Calculation logic
            pivot_table = pd.pivot_table(
                filtered_df, values='tpv', index='receiver_name', 
                columns='pg_name', aggfunc='sum', fill_value=0
            )
            pivot_tpv_cr = pivot_table / 10000000
            pivot_tpv_cr['Grand Total (Cr)'] = pivot_tpv_cr.sum(axis=1)
            pivot_tpv_cr = pivot_tpv_cr.sort_values(by='Grand Total (Cr)', ascending=False)

            # --- UI LAYOUT ---
            
            # Row 1: Metrics
            col1, col2, col3 = st.columns(3)
            total_tpv = pivot_tpv_cr['Grand Total (Cr)'].sum()
            col1.metric("Total TPV (Cr)", f"₹{total_tpv:,.2f}")
            col2.metric("Active Receivers", len(pivot_tpv_cr))
            col3.metric("Records Found", f"{len(filtered_df):,}")

            # Row 2: Visual & Table Split
            tab1, tab2 = st.tabs(["📈 Data Visualization", "📋 Detailed Table"])
            
            with tab1:
                fig = px.bar(
                    pivot_tpv_cr.drop(columns='Grand Total (Cr)'), 
                    barmode="group",
                    title="TPV Distribution by PG Name",
                    labels={'value': 'Amount (Cr)', 'receiver_name': 'Merchant'},
                    template="plotly_white"
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                st.dataframe(
                    pivot_tpv_cr.style.format("{:.2f}").background_gradient(cmap='Blues', subset=['Grand Total (Cr)']),
                    use_container_width=True,
                    height=400
                )
                
            # Download Button
            csv = pivot_tpv_cr.to_csv().encode('utf-8')
            st.download_button("📥 Download Report as CSV", data=csv, file_name="tpv_report.csv", mime="text/csv")

        else:
            st.warning("⚠️ No data matches the receiver names provided.")
            
    except Exception as e:
        st.error(f"Error processing file: {e}")
else:
    # Landing State UI
    st.info("👋 Welcome! Please upload your CSV file in the sidebar to generate the TPV report.")
