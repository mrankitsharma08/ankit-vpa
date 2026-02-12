import streamlit as st
import pandas as pd
import plotly.express as px
import gc

# 1. Page Configuration
st.set_page_config(page_title="TPV PG Share Analyzer", layout="wide")

st.title("📊 PG Share Analyzer (Cr)")
st.markdown("---")

# 2. Sidebar for Controls
with st.sidebar:
    st.header("1. Data Upload")
    uploaded_file = st.file_uploader("Upload your CSV file", type="csv")
    
    st.divider()
    st.header("2. Analysis Settings")
    merchant_input = st.text_input("Enter Receiver Names (comma separated)", "Amazon, Flipkart")
    top_n = st.slider("Show Top 'N' Merchants in Chart", 5, 20, 10)
    
    st.divider()
    st.header("3. Maintenance")
    if st.button("🧹 Clear App Cache"):
        st.cache_data.clear()
        st.success("Memory cleared!")
        st.rerun()

# 3. Smart Column Mapper Function
def get_column_mapping(df_cols):
    mapping = {}
    # Define what we are looking for and common aliases
    targets = {
        'receiver_name': ['receiver_name', 'merchant', 'beneficiary'],
        'tpv': ['tpv', 'amount', 'transaction_value'],
        'pg_name': ['pg_name', 'gateway', 'payment_gateway']
    }
    
    st.write("### 🛠 Confirm Column Mapping")
    cols = st.columns(3)
    
    for i, (key, aliases) in enumerate(targets.items()):
        # Default to the first match found in CSV
        default_idx = 0
        for alias in aliases:
            if alias in [c.lower() for c in df_cols]:
                default_idx = [c.lower() for c in df_cols].index(alias)
                break
        mapping[key] = cols[i].selectbox(f"Map '{key}' to:", df_cols, index=default_idx)
    return mapping

# 4. Main Processing Logic
if uploaded_file:
    try:
        # Load headers to setup mapping
        header_df = pd.read_csv(uploaded_file, nrows=0)
        col_map = get_column_mapping(header_df.columns.tolist())
        
        if st.button("🚀 Generate Report"):
            # Load data with only required columns to save RAM
            selected_cols = list(col_map.values())
            df = pd.read_csv(uploaded_file, usecols=selected_cols, engine='c')
            
            # Standardize names for internal logic
            inv_map = {v: k for k, v in col_map.items()}
            df = df.rename(columns=inv_map)
            
            # Optimization: Convert types
            df['tpv'] = pd.to_numeric(df['tpv'], errors='coerce', downcast='float').fillna(0)
            
            # Filtering
            targets = [t.strip().lower() for t in merchant_input.split(',') if t.strip()]
            filtered_df = df[df['receiver_name'].astype(str).str.lower().isin(targets)].copy()
            
            if not filtered_df.empty:
                # Pivot Table Calculation
                pivot = pd.pivot_table(filtered_df, values='tpv', index='receiver_name', 
                                       columns='pg_name', aggfunc='sum', fill_value=0)
                
                # Currency Conversion (Crores)
                pivot_cr = pivot / 10_000_000
                pivot_cr['Grand Total (Cr)'] = pivot_cr.sum(axis=1)
                pivot_cr = pivot_cr.sort_values(by='Grand Total (Cr)', ascending=False)
                
                # --- UI DASHBOARD ---
                st.divider()
                m1, m2 = st.columns(2)
                m1.metric("Total TPV Analyzed", f"₹{pivot_cr['Grand Total (Cr)'].sum():,.2f} Cr")
                m2.metric("Filtered Records", f"{len(filtered_df):,}")
                
                tab1, tab2 = st.tabs(["📈 Market Share Chart", "📋 Data Table"])
                
                with tab1:
                    # Logic for "Others" grouping in Chart
                    chart_data = pivot_cr.head(top_n).drop(columns='Grand Total (Cr)')
                    if len(pivot_cr) > top_n:
                        others = pivot_cr.iloc[top_n:].sum(numeric_only=True).drop('Grand Total (Cr)')
                        others_df = pd.DataFrame([others], index=['Others'])
                        chart_data = pd.concat([chart_data, others_df])
                    
                    # Melt for Plotly
                    v_df = chart_data.reset_index().rename(columns={'index': 'Merchant'})
                    v_melt = v_df.melt(id_vars='Merchant', var_name='PG', value_name='Cr')
                    fig = px.bar(v_melt, x='Merchant', y='Cr', color='PG', barmode='group', template="plotly_white")
                    st.plotly_chart(fig, use_container_width=True)
                
                with tab2:
                    st.dataframe(pivot_cr.style.format("{:.2f}"), use_container_width=True)
                    csv_data = pivot_cr.to_csv().encode('utf-8')
                    st.download_button("📥 Download Report CSV", data=csv_data, file_name="tpv_pg_share.csv")
                
                # Explicit RAM cleanup
                del filtered_df, df
                gc.collect()
            else:
                st.warning("No matches found. Please check your spelling of the receiver names.")
    except Exception as e:
        st.error(f"Analysis Error: {e}")
else:
    st.info("👋 To begin, upload your January VPA data CSV in the sidebar.")
