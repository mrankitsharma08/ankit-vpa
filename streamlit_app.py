import streamlit as st
import pandas as pd
import plotly.express as px
import gc

# 1. Page Configuration
st.set_page_config(page_title="TPV PG Share Analyzer", layout="wide")

st.title("📊 PG Share Analyzer (Cr)")
st.info("Upload your VPA data to see Merchant-wise PG distribution.")

# 2. Sidebar for Controls
with st.sidebar:
    st.header("1. Data Upload")
    uploaded_file = st.file_uploader("Upload CSV file", type="csv")
    
    st.divider()
    st.header("2. Analysis Settings")
    merchant_input = st.text_input("Enter Receiver Names (comma separated)", "Amazon, Flipkart")
    top_n = st.slider("Show Top 'N' Merchants in Chart", 5, 20, 10)
    
    st.divider()
    if st.button("🧹 Clear App Cache"):
        st.cache_data.clear()
        st.success("Memory cleared!")
        st.rerun()

# 3. Optimized Loading Function (Fixed Column Names)
@st.cache_data(show_spinner="Reading large file...")
def load_data_direct(file):
    # Directly using your specified headers
    cols = ['pg_name', 'receiver_name', 'tpv']
    
    df = pd.read_csv(file, usecols=cols, engine='c', low_memory=True)
    
    # Memory Optimization
    df['tpv'] = pd.to_numeric(df['tpv'], errors='coerce', downcast='float').fillna(0)
    df['receiver_name'] = df['receiver_name'].astype('category')
    df['pg_name'] = df['pg_name'].astype('category')
    
    return df

# 4. Main Logic
if uploaded_file:
    try:
        # Load data
        df = load_data_direct(uploaded_file)
        
        # Filtering
        targets = [t.strip().lower() for t in merchant_input.split(',') if t.strip()]
        filtered_df = df[df['receiver_name'].astype(str).str.lower().isin(targets)].copy()
        
        if not filtered_df.empty:
            # Pivot Table Calculation (Aggregating TPV)
            pivot = pd.pivot_table(filtered_df, values='tpv', index='receiver_name', 
                                   columns='pg_name', aggfunc='sum', fill_value=0)
            
            # Convert to Crores
            pivot_cr = pivot / 10_000_000
            pivot_cr['Grand Total (Cr)'] = pivot_cr.sum(axis=1)
            pivot_cr = pivot_cr.sort_values(by='Grand Total (Cr)', ascending=False)
            
            # --- DASHBOARD UI ---
            st.divider()
            m1, m2 = st.columns(2)
            m1.metric("Total Selected TPV", f"₹{pivot_cr['Grand Total (Cr)'].sum():,.2f} Cr")
            m2.metric("Records Found", f"{len(filtered_df):,}")
            
            tab1, tab2 = st.tabs(["📈 Market Share Chart", "📋 Detailed Table"])
            
            with tab1:
                # Group "Others" for cleaner visualization
                chart_data = pivot_cr.head(top_n).drop(columns='Grand Total (Cr)')
                if len(pivot_cr) > top_n:
                    others_sum = pivot_cr.iloc[top_n:].sum(numeric_only=True).drop('Grand Total (Cr)')
                    others_df = pd.DataFrame([others_sum], index=['Others'])
                    chart_data = pd.concat([chart_data, others_df])
                
                # Melt for Plotly Chart
                v_df = chart_data.reset_index().rename(columns={'index': 'Merchant'})
                v_melt = v_df.melt(id_vars='Merchant', var_name='PG', value_name='Cr')
                fig = px.bar(v_melt, x='Merchant', y='Cr', color='PG', barmode='group', template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
            
            with tab2:
                st.dataframe(pivot_cr.style.format("{:.2f}"), use_container_width=True)
                csv = pivot_cr.to_csv().encode('utf-8')
                st.download_button("📥 Download This Report", data=csv, file_name="tpv_report.csv")
            
            # Explicit cleanup
            del filtered_df, df
            gc.collect()
            
        else:
            st.warning("No matches found for the merchant names provided.")
            
    except ValueError as e:
        st.error(f"Column Error: Ensure your CSV contains 'pg_name', 'receiver_name', and 'tpv'.")
    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Please upload your CSV to begin. The app will process it into Crores automatically.")
