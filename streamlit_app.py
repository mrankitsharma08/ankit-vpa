import streamlit as st
import pandas as pd
import gc

# 1. Page Configuration
st.set_page_config(page_title="Excel-Style TPV Loader", layout="wide")

st.title("📂 Interactive TPV Data Loader")
st.markdown("Upload your file to view, edit, and explore it like a spreadsheet.")

# 2. Sidebar for Controls
with st.sidebar:
    st.header("Settings")
    uploaded_file = st.file_uploader("Upload Marketshare CSV", type="csv")
    
    if st.button("🧹 Clear App Memory"):
        st.cache_data.clear()
        st.rerun()

# 3. Flexible Loading Function
@st.cache_data(show_spinner="Cleaning and loading data...")
def load_and_clean_data(file):
    try:
        # Step A: Detect separator (comma or tab) automatically
        # Use sep=None to handle \t (tabs) that often cause 'Usecols' errors
        df = pd.read_csv(file, sep=None, engine='python')
        
        # Step B: Clean column names (Removes hidden spaces and tabs)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Step C: Optimization - Downcast numeric TPV if it exists
        if 'tpv' in df.columns:
            df['tpv'] = pd.to_numeric(df['tpv'], errors='coerce').fillna(0)
            
        return df, None
    except Exception as e:
        return None, str(e)

# 4. Main App Interface
if uploaded_file:
    df, error = load_and_clean_data(uploaded_file)
    
    if error:
        st.error(f"❌ Error reading file: {error}")
    else:
        st.success(f"✅ Successfully loaded {len(df):,} rows!")
        
        # --- THE INTERACTIVE EXCEL UI ---
        st.subheader("📝 Data Editor (Excel Mode)")
        st.write("You can click on headers to sort, or double-click cells to edit.")
        
        # st.data_editor is the most powerful interactive table in Streamlit
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic", # Allows you to add/delete rows
            height=500
        )
        
        # --- QUICK SUMMARY (AUTO PIVOT) ---
        if st.checkbox("Show Summary (Receiver wise PG Share in Cr)"):
            try:
                # Pivot logic
                pivot = pd.pivot_table(
                    edited_df, 
                    values='tpv', 
                    index='receiver_name', 
                    columns='pg_name', 
                    aggfunc='sum', 
                    fill_value=0
                )
                
                # Convert to Crores
                pivot_cr = pivot / 10_000_000
                pivot_cr['Grand Total (Cr)'] = pivot_cr.sum(axis=1)
                
                st.subheader("📊 Summary Report (Crores)")
                st.dataframe(pivot_cr.style.format("{:.2f}"), use_container_width=True)
                
                # Download Button for your custom pivot
                st.download_button(
                    label="📥 Download Pivot as CSV",
                    data=pivot_cr.to_csv().encode('utf-8'),
                    file_name="tpv_pivot_report.csv",
                    mime="text/csv"
                )
            except KeyError as e:
                st.warning(f"Required columns (receiver_name, pg_name, tpv) not found for auto-pivot. Use the table above to check names.")

        # RAM Management
        gc.collect()

else:
    st.info("👋 Upload your CSV file to get started.")
