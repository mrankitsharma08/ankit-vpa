import streamlit as st
import pandas as pd
import gc

# 1. Page Configuration
st.set_page_config(page_title="VPA TPV Analyzer", layout="wide")

st.title("📊 VPA TPV Analysis Dashboard")
st.markdown("---")

# --- SIDEBAR: INPUTS & MEMORY ---
with st.sidebar:
    st.header("1. Data Center")
    uploaded_file = st.file_uploader("Upload Marketshare CSV", type="csv")
    
    st.divider()
    st.header("2. Search Filters")
    # Using a text area for multiple merchants to avoid UI lag
    merchant_input = st.text_area("Enter Receiver Names (one per line or comma separated)", 
                                  placeholder="Amazon, Flipkart, Myntra")
    
    st.divider()
    if st.button("🧹 Reset App Memory"):
        st.cache_data.clear()
        st.success("Cache cleared! Upload a new file.")
        st.rerun()

# --- OPTIMIZED LOADING LOGIC ---
if uploaded_file:
    try:
        # STEP 1: Peek at headers only (Fastest way to avoid hangs)
        # We read 0 rows to get the column list safely
        df_header = pd.read_csv(uploaded_file, nrows=0, sep=None, engine='python')
        all_columns = [str(c).strip() for c in df_header.columns]

        st.subheader("🛠️ Step 1: Configure Your Pivot")
        
        c1, c2 = st.columns(2)
        with c1:
            # User picks the columns from their file
            sel_receiver = st.selectbox("Select 'Receiver Name' Column:", all_columns, 
                                        index=all_columns.index('receiver_name') if 'receiver_name' in all_columns else 0)
        with c2:
            sel_pg = st.selectbox("Select 'PG Name' Column:", all_columns,
                                  index=all_columns.index('pg_name') if 'pg_name' in all_columns else 0)
        
        # We assume 'tpv' is always the value; finding it automatically
        tpv_col = st.selectbox("Select 'TPV' Column:", all_columns,
                               index=all_columns.index('tpv') if 'tpv' in all_columns else 0)

        # STEP 2: The "Action" Button
        if st.button("🚀 Process & Generate Report"):
            with st.spinner("Processing large dataset..."):
                # Load ONLY the necessary columns to save ~80% RAM
                # file.seek(0) ensures we read from the start
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, usecols=[sel_receiver, sel_pg, tpv_col], engine='c')
                
                # Standardize column names for the logic
                df.columns = ['pg_name', 'receiver_name', 'tpv']
                
                # Numeric optimization
                df['tpv'] = pd.to_numeric(df['tpv'], errors='coerce').fillna(0)
                
                # Step 3: Filtering
                targets = [t.strip().lower() for t in merchant_input.replace('\n', ',').split(',') if t.strip()]
                
                if targets:
                    filtered_df = df[df['receiver_name'].astype(str).str.lower().isin(targets)].copy()
                else:
                    filtered_df = df.copy()

                if not filtered_df.empty:
                    # Step 4: Pivot Math
                    pivot = pd.pivot_table(
                        filtered_df, 
                        values='tpv', 
                        index='receiver_name', 
                        columns='pg_name', 
                        aggfunc='sum', 
                        fill_value=0
                    )
                    
                    # Currency Conversion (Crores)
                    pivot_cr = pivot / 10_000_000
                    pivot_cr['Grand Total (Cr)'] = pivot_cr.sum(axis=1)
                    pivot_cr = pivot_cr.sort_values(by='Grand Total (Cr)', ascending=False)

                    # --- UI RESULTS ---
                    st.divider()
                    st.success(f"Successfully processed {len(filtered_df):,} records!")
                    
                    st.subheader("📋 Receiver-wise PG Share (in Crores)")
                    st.dataframe(pivot_cr.style.format("{:.2f}"), use_container_width=True)
                    
                    # Download
                    st.download_button("📥 Export Pivot to CSV", 
                                       pivot_cr.to_csv().encode('utf-8'), 
                                       "tpv_pg_report.csv")
                else:
                    st.warning("No matches found for the merchant names provided.")
                
                # Forced Garbage Collection to prevent hanging
                del df
                gc.collect()

    except Exception as e:
        st.error(f"⚠️ **Debug Info:** {e}")
        st.info("Ensure your CSV isn't open in another program and headers are clean.")
else:
    st.info("👋 Upload your VPA CSV in the sidebar to start.")
