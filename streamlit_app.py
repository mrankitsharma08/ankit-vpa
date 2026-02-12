import streamlit as st
import pandas as pd
import plotly.express as px
import gc

# UI Configuration
st.set_page_config(page_title="TPV PG Analyzer", layout="wide")

st.title("📊 PG Share Analyzer (Cr)")
st.markdown("---")

# --- SIDEBAR ---
with st.sidebar:
    st.header("📂 Data Source")
    uploaded_file = st.file_uploader("Upload Marketshare CSV", type="csv")
    
    st.divider()
    st.header("🔍 Filters")
    merchant_input = st.text_input("Receiver Names (comma separated)", "Amazon, Flipkart")
    
    if st.button("🧹 Clear App Cache"):
        st.cache_data.clear()
        st.rerun()

# --- MAIN LOGIC ---
if uploaded_file:
    try:
        # STEP 1: Read only the headers (Fast & Memory Safe)
        # This prevents the "Oh no" crash by not loading 200MB yet
        header_df = pd.read_csv(uploaded_file, nrows=0)
        all_columns = header_df.columns.tolist()

        st.subheader("🛠️ Step 1: Configure Your Columns")
        st.info("Select which columns in your file correspond to the required fields.")
        
        col1, col2, col3 = st.columns(3)
        
        # Smart detection of column names
        def find_default(options, target):
            for opt in options:
                if target.lower() in opt.lower():
                    return options.index(opt)
            return 0

        with col1:
            sel_receiver = st.selectbox("Receiver Name Column", all_columns, index=find_default(all_columns, "receiver"))
        with col2:
            sel_pg = st.selectbox("PG Name Column", all_columns, index=find_default(all_columns, "pg_name"))
        with col3:
            sel_tpv = st.selectbox("TPV Column", all_columns, index=find_default(all_columns, "tpv"))

        # STEP 2: Process Button
        if st.button("🚀 Process & Generate Pivot"):
            with st.spinner("Analyzing data..."):
                # Load ONLY the 3 selected columns to save RAM
                df = pd.read_csv(uploaded_file, usecols=[sel_receiver, sel_pg, sel_tpv], engine='c')
                
                # Standardize names for internal math
                df = df.rename(columns={sel_receiver: 'receiver', sel_pg: 'pg', sel_tpv: 'tpv'})
                
                # Clean numeric data
                df['tpv'] = pd.to_numeric(df['tpv'], errors='coerce').fillna(0)
                
                # Filter by user input
                targets = [t.strip().lower() for t in merchant_input.split(',') if t.strip()]
                filtered_df = df[df['receiver'].astype(str).str.lower().isin(targets)].copy()

                if not filtered_df.empty:
                    # Create Pivot Table
                    pivot = pd.pivot_table(filtered_df, values='tpv', index='receiver', 
                                           columns='pg', aggfunc='sum', fill_value=0)
                    
                    # Convert to Crores
                    pivot_cr = pivot / 10_000_000
                    pivot_cr['Grand Total (Cr)'] = pivot_cr.sum(axis=1)
                    pivot_cr = pivot_cr.sort_values(by='Grand Total (Cr)', ascending=False)

                    # --- DASHBOARD UI ---
                    st.divider()
                    m1, m2 = st.columns(2)
                    m1.metric("Total TPV (Cr)", f"₹{pivot_cr['Grand Total (Cr)'].sum():,.2f}")
                    m2.metric("Filtered Records", f"{len(filtered_df):,}")

                    tab1, tab2 = st.tabs(["📈 PG Share Chart", "📋 Detailed Table"])
                    
                    with tab1:
                        # Prepare data for chart (exclude Grand Total)
                        v_df = pivot_cr.drop(columns='Grand Total (Cr)').reset_index()
                        v_melt = v_df.melt(id_vars='receiver', var_name='PG', value_name='Cr')
                        fig = px.bar(v_melt, x='receiver', y='Cr', color='pg', 
                                     barmode='group', template='plotly_white')
                        st.plotly_chart(fig, use_container_width=True)

                    with tab2:
                        st.dataframe(pivot_cr.style.format("{:.2f}"), use_container_width=True)
                        st.download_button("📥 Download Report", pivot_cr.to_csv().encode('utf-8'), "tpv_report.csv")
                
                else:
                    st.warning("No data found for the specified merchants. Check spelling or column selection.")
                
                # Garbage collection to keep RAM low
                gc.collect()

    except Exception as e:
        st.error(f"⚠️ **Application Error:** {e}")
else:
    st.info("👋 **Waiting for data...** Please upload your CSV in the sidebar.")
