import streamlit as st
import pandas as pd
import gc
import re

# --- 1. FUNCTIONS ---

def get_gdrive_download_url(url):
    """
    Converts a standard Google Drive sharing link into a direct download link.
    """
    if "drive.google.com" not in url:
        return url
    
    file_id_match = re.search(r'd/([a-zA-Z0-9-_]+)', url)
    if file_id_match:
        file_id = file_id_match.group(1)
        return f'https://drive.google.com/uc?export=download&id={file_id}'
    return url

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="VPA TPV Analyzer", layout="wide")

st.title("📊 VPA TPV Analysis Dashboard")
st.markdown("---")

# --- 3. SIDEBAR: INPUTS & MEMORY ---
with st.sidebar:
    st.header("1. Data Center")
    
    data_source = st.radio("Select Data Source:", ["Local CSV", "Google Drive Link"])
    
    uploaded_file = None
    gdrive_url = None

    if data_source == "Local CSV":
        uploaded_file = st.file_uploader("Upload Marketshare CSV", type="csv")
    else:
        gdrive_url = st.text_input("Paste Google Drive Link:", 
                                  placeholder="https://drive.google.com/file/d/...")
        st.caption("⚠️ Ensure 'Anyone with the link' is enabled on Google Drive.")
    
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

# --- 4. DATA PROCESSING LOGIC ---

# Determine the source path
active_source = uploaded_file if data_source == "Local CSV" else gdrive_url

if active_source:
    try:
        # Convert link if necessary
        file_path = active_source
        if data_source == "Google Drive Link":
            file_path = get_gdrive_download_url(gdrive_url)

        # Step 1: Detect Headers (Fast read)
        # Using a small chunk to get column names without loading the file
        df_header = pd.read_csv(file_path, nrows=2)
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
            with st.spinner("Streaming data from source..."):
                
                # Load only required columns and use memory-efficient types
                load_cols = [sel_receiver, sel_pg, tpv_col]
                if include_vpa and sel_vpa:
                    load_cols.append(sel_vpa)
                
                # Reading with memory optimizations
                # engine='c' is faster; low_memory=True prevents RAM spikes
                df = pd.read_csv(file_path, usecols=load_cols, engine='c', low_memory=True)
                
                # Standardize column names
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

                # Cleanup original df to free RAM immediately
                del df
                gc.collect()

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
                    
                    # A. Add Horizontal Grand Total
                    pivot_cr['Grand Total (Cr)'] = pivot_cr.sum(axis=1)
                    
                    # B. Sort by Grand Total
                    pivot_cr = pivot_cr.sort_values(by='Grand Total (Cr)', ascending=False)

                    # C. Add Vertical Grand Total
                    total_row_label = ("TOTAL", "") if include_vpa else "TOTAL"
                    pivot_cr.loc[total_row_label, :] = pivot_cr.sum(axis=0)

                    # UI Display
                    st.divider()
                    st.success(f"Successfully processed {len(filtered_df):,} matching records.")
                    
                    # Styling: Formatting decimals
                    styled_df = pivot_cr.style.format("{:.2f}").highlight_max(
                        axis=0, 
                        subset=pd.IndexSlice[total_row_label, :]
                    )
                    
                    st.dataframe(styled_df, use_container_width=True)
                    
                    # Prepare download
                    csv_data = pivot_cr.to_csv().encode('utf-8')
                    st.download_button("📥 Download Report", csv_data, "vpa_analysis_report.csv")
                else:
                    st.warning("No data matches your search criteria.")
                
                # Final memory cleanup
                del filtered_df
                gc.collect()

    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.info("Check if your Google Drive link is public and if the column names are correct.")
else:
    st.info("👋 Provide a Google Drive link or upload a CSV in the sidebar to begin.")
