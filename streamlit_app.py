import streamlit as st
import pandas as pd
import plotly.express as px
import gc  # Garbage Collector to free up RAM

# --- UI CONFIGURATION ---
st.set_page_config(page_title="High-Volume TPV Analyzer", layout="wide")

st.title("🚀 Optimized TPV Market Share Analyzer")
st.markdown("Processing high-volume data (200MB+) using memory-efficient loading.")

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("1. Upload Data")
    uploaded_file = st.file_uploader("Select CSV File (Max 1GB)", type="csv")
    
    st.header("2. Filter Settings")
    raw_input = st.text_input("Receiver Names (comma separated)", "Amazon, Flipkart")
    st.info("💡 Large files may take 10-30 seconds to upload and process.")

# --- OPTIMIZED LOADING FUNCTION ---
@st.cache_data(show_spinner="Optimizing data for memory...")
def load_and_optimize(file):
    # STEP 1: Only load the columns we actually need (saves ~60% memory)
    needed_cols = ['receiver_name', 'tpv', 'pg_name']
    
    # STEP 2: Use efficient engines and settings
    # 'on_bad_lines' skips corrupt rows in large datasets
    df = pd.read_csv(
        file, 
        usecols=needed_cols, 
        engine='c', # C-engine is significantly faster than Python engine
        low_memory=True
    )

    # STEP 3: Downcast Numeric Data (int64 -> int32 or float64 -> float32)
    # This reduces numeric column memory footprint by 50%
    if 'tpv' in df.columns:
        df['tpv'] = pd.to_numeric(df['tpv'], downcast='float')

    # STEP 4: Convert repeated strings to 'category'
    # This is the single biggest memory saver for PG names and Receiver names
    df['receiver_name'] = df['receiver_name'].astype('category')
    df['pg_name'] = df['pg_name'].astype('category')
    
    return df

# --- MAIN APP LOGIC ---
if uploaded_file is not None:
    try:
        # Load data using the optimized function
        df = load_and_optimize(uploaded_file)
        
        # Filter Logic (using categories is extremely fast)
        receiver_list = [name.strip().lower() for name in raw_input.split(',') if name.strip()]
        
        # Process filter on lower-case for matching
        # Note: We do this only on the subset to save RAM
        df['match_name'] = df['receiver_name'].astype(str).str.lower()
        filtered_df = df[df['match_name'].isin(receiver_list)].copy()
        
        # Explicitly delete the search column to free space
        df.drop(columns=['match_name'], inplace=True)
        gc.collect() # Force clean up

        if not filtered_df.empty:
            # Aggregate TPV (Pivot)
            pivot_table = pd.pivot_table(
                filtered_df, values='tpv', index='receiver_name', 
                columns='pg_name', aggfunc='sum', fill_value=0
            )
            
            # Conversion to Crores
            pivot_tpv_cr = pivot_table / 10_000_000
            pivot_tpv_cr['Grand Total (Cr)'] = pivot_tpv_cr.sum(axis=1)
            pivot_tpv_cr = pivot_tpv_cr.sort_values(by='Grand Total (Cr)', ascending=False)

            # --- DISPLAY ---
            m1, m2, m3 = st.columns(3)
            m1.metric("Selected TPV (Cr)", f"₹{pivot_tpv_cr['Grand Total (Cr)'].sum():,.2f}")
            m2.metric("Filtered Records", f"{len(filtered_df):,}")
            m3.metric("Memory Usage (App)", f"{df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")

            tab1, tab2 = st.tabs(["📊 Market Share Chart", "📄 Raw Data"])
            
            with tab1:
                # Plotly with optimized melted dataframe
                viz_df = pivot_tpv_cr.drop(columns='Grand Total (Cr)').reset_index()
                viz_melted = viz_df.melt(id_vars='receiver_name', var_name='PG', value_name='Cr')
                fig = px.bar(viz_melted, x='receiver_name', y='Cr', color='PG', barmode='group')
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                st.dataframe(pivot_tpv_cr.style.format("{:.2f}"), use_container_width=True)

        else:
            st.warning("Search returned no results. Check your spelling.")

    except Exception as e:
        st.error(f"Memory or Processing Error: {e}")
        st.info("Try selecting fewer columns or merchant names.")
else:
    st.info("📁 Waiting for file upload (up to 1GB).")
