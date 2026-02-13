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
    search_input = st.text_area("Enter Receiver Names or VPAs", 
                                  placeholder="Amazon, merchant@upi, Flipkart",
                                  help="Enter names or specific VPA IDs separated by commas or new lines.")
    
    st.divider()
    st.header("3. Drilldown Options")
    include_vpa = st.toggle("Include VPA in Report", value=False)
    
    st.divider()
    if st.button("🧹 Reset App Memory"):
        st.cache_data.clear()
        st.success("Cache cleared!")
        st.rerun()

# --- OPTIMIZED LOADING LOGIC ---
if uploaded_file:
    try:
        # Step 1: Detect Headers
        df_header = pd.read_csv(uploaded_file, nrows=0, sep=None, engine='python')
        all_columns = [str(c).strip() for c in df_header.columns]

        st.subheader("🛠️ Step 1: Column Mapping")
        
        cols = st.columns(3 if not include_vpa else 4)
        
        with cols[0]:
            sel_receiver = st.selectbox("Receiver Name Column:", all_columns, 
                                        index=all_columns.index('receiver_name') if 'receiver_name' in all_columns else 0)
        with cols[1]:
            sel_pg = st.selectbox("PG Name Column:", all_columns,
                                  index=all_columns.index('pg_name') if 'pg_name' in all_columns else 0)
        with cols[2]:
            tpv_col = st.selectbox("TPV Column:", all_columns,
                                   index=all_columns.index('tpv') if 'tpv' in all_columns else 0)
            
        sel_vpa = None
        if include_vpa:
            with cols[3]:
                sel_vpa = st.selectbox("VPA ID Column:", all_columns,
                                       index=all_columns.index('vpa') if 'vpa' in all_columns else 0)

        # STEP 2: Process Button
        if st.button("🚀 Generate Merchant & VPA Report"):
            with st.spinner("Crunching data..."):
                uploaded_file.seek(0)
                
                # Load only required columns
                load_cols = [sel_receiver, sel_pg, tpv_col]
                if include_vpa and sel_vpa:
                    load_cols.append(sel_vpa)
                
                df = pd.read_csv(uploaded_file, usecols=load_cols, engine='c')
                
                # Standardize names
                rename_map = {sel_receiver: 'receiver_name', sel_pg: 'pg_name', tpv_col: 'tpv'}
                if include_vpa:
                    rename_map[sel_vpa] = 'vpa_id'
                df.rename(columns=rename_map, inplace=True)
                
                # Clean TPV data
                df['tpv'] = pd.to_numeric(df['tpv'], errors='coerce').fillna(0)
                
                # Step 3: Global Filtering
                targets = [t.strip().lower() for t in search_input.replace('\n', ',').split(',') if t.strip()]
                
                if targets:
                    mask = df['receiver_name'].astype(str).str.lower().isin(targets)
                    if include_vpa:
                        mask = mask | df['vpa_id'].astype(str).str.lower().isin(targets)
                    filtered_df = df[mask].copy()
                else:
                    filtered_df = df.copy()

                if not filtered_df.empty:
                    # Step 4: Pivot Logic
                    pivot_idx = ['receiver_name', 'vpa_id'] if include_vpa else 'receiver_name'
                    
                    pivot = pd.pivot_table(
                        filtered_df, 
                        values='tpv', 
                        index=pivot_idx, 
                        columns='pg_name', 
                        aggfunc='sum', 
                        fill_value=0
                    )
                    
                    # Formatting to Crores
                    pivot_cr = pivot / 10_000_000
                    
                    # A. Add Horizontal Grand Total (Sum across PGs for each merchant)
                    pivot_cr['Grand Total (Cr)'] = pivot_cr.sum(axis=1)
                    
                    # B. Sort by Grand Total before adding the Vertical Total
                    pivot_cr = pivot_cr.sort_values(by='Grand Total (Cr)', ascending=False)

                    # C. Add Vertical Grand Total (Sum of all rows)
                    # We use a tuple for the index if it's a MultiIndex (Merchant + VPA)
                    total_row_label = ("TOTAL", "") if include_vpa else "TOTAL"
                    pivot_cr.loc[total_row_label, :] = pivot_cr.sum(axis=0)

                    # UI Display
                    st.divider()
                    st.success(f"Matched {len(filtered_df):,} records.")
                    
                    # Styling: Formatting decimals and highlighting the Total row
                    styled_df = pivot_cr.style.format("{:.2f}").highlight_max(
                        axis=0, 
                        subset=pd.IndexSlice[total_row_label, :], 
                        color="#2e7d32"
                    )
                    
                    st.dataframe(styled_df, use_container_width=True)
                    
                    st.download_button("📥 Download Report", 
                                       pivot_cr.to_csv().encode('utf-8'), 
                                       "vpa_analysis.csv")
                else:
                    st.warning("No data matches your search criteria.")
                
                del df
                gc.collect()

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("👋 Please upload your CSV file in the sidebar to begin.")
