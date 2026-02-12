import streamlit as st
import pandas as pd
import plotly.express as px

# UI Configuration
st.set_page_config(page_title="TPV Analyzer Pro", layout="wide")

st.title("📊 TPV Market Share Analyzer")
st.divider()

# Sidebar for Setup & Inputs
with st.sidebar:
    st.header("1. Data Source")
    uploaded_file = st.file_uploader("Upload Marketshare CSV", type="csv")
    
    st.header("2. Analysis Filters")
    # Default values included for immediate feedback
    raw_input = st.text_input("Receiver Names (comma separated)", "Amazon, Flipkart, Myntra")

if uploaded_file is not None:
    try:
        # Load and detect separator automatically
        df = pd.read_csv(uploaded_file, sep=None, engine='python')
        
        # Data Processing
        receiver_list = [name.strip().lower() for name in raw_input.split(',') if name.strip()]
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
            # Metrics Row
            total_tpv = pivot_tpv_cr['Grand Total (Cr)'].sum()
            m1, m2, m3 = st.columns(3)
            m1.metric("Total TPV (Cr)", f"₹{total_tpv:,.2f}")
            m2.metric("Active Merchants", len(pivot_tpv_cr))
            m3.metric("Records Found", f"{len(filtered_df):,}")

            # Tabs for Viz and Data
            tab1, tab2 = st.tabs(["📈 Chart View", "📋 Table View"])
            
            with tab1:
                # Prepare data for Plotly
                viz_df = pivot_tpv_cr.drop(columns='Grand Total (Cr)').reset_index()
                viz_melted = viz_df.melt(id_vars='receiver_name', var_name='PG Name', value_name='TPV (Cr)')
                
                fig = px.bar(
                    viz_melted, x='receiver_name', y='TPV (Cr)', color='PG Name',
                    title="TPV Distribution by Payment Gateway",
                    barmode="group", template="plotly_white"
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                st.dataframe(pivot_tpv_cr.style.format("{:.2f}"), use_container_width=True)
                
            # Download Button
            csv_data = pivot_tpv_cr.to_csv().encode('utf-8')
            st.download_button("📥 Download This Report", data=csv_data, file_name="tpv_report.csv")

        else:
            st.warning("No data found for the names entered in the sidebar.")
            
    except Exception as e:
        st.error(f"Analysis Error: {e}")
else:
    st.info("Please upload your CSV file in the sidebar to start.")
