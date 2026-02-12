import streamlit as st
import pandas as pd
import plotly.express as px
import gc

st.set_page_config(page_title="Ultimate TPV Analyzer", layout="wide")

st.title("PhonePe PG Market Share Analyzer")
st.markdown("---")

# --- SIDEBAR: CONTROLS & LOGIC ---
with st.sidebar:
    st.header("1. Data Source")
    uploaded_file = st.file_uploader("Upload Marketshare CSV", type="csv")
    
    st.divider()
    st.header("2. Analysis Filters")
    merchant_input = st.text_input("Merchants (comma separated)", "Amazon, Flipkart, Myntra")
    
    st.divider()
    st.header("3. Visual Settings")
    # New: Slider to control grouping
    top_n = st.slider("Show Top 'N' Merchants in Chart", 5, 20, 10)
    st.caption("Other merchants will be grouped into 'Others'")

    st.divider()
    st.header("4. System Tools")
    if st.button("🧹 Clear App Cache"):
        st.cache_data.clear()
        st.success("Cache cleared!")
        st.rerun()

# --- SMART MAPPING FUNCTION ---
def get_column_mapping(available_cols):
    mapping = {}
    targets = {
        'receiver_name': ['receiver_name', 'merchant', 'beneficiary', 'client'],
        'tpv': ['tpv', 'amount', 'transaction_value', 'value'],
        'pg_name': ['pg_name', 'gateway', 'payment_gateway', 'pg']
    }
    
    st.write("### 🛠 Column Mapping")
    st.info("Ensure the app identified your CSV columns correctly:")
    cols = st.columns(3)
    
    for i, (key, aliases) in enumerate(targets.items()):
        default_idx = 0
        for alias in aliases:
            if alias in [c.lower() for c in available_cols]:
                default_idx = [c.lower() for c in available_cols].index(alias)
                break
        mapping[key] = cols[i].selectbox(f"Select {key}:", available_cols, index=default_idx)
    return mapping

# --- MAIN LOGIC ---
if uploaded_file:
    try:
        # Step 1: Map Columns
        header_check = pd.read_csv(uploaded_file, nrows=0)
        col_map = get_column_mapping(header_check.columns.tolist())
        
        if st.button("🚀 Run Analysis"):
            # Step 2: Load Optimized
            df = pd.read_csv(uploaded_file, usecols=list(col_map.values()), engine='c')
            inv_map = {v: k for k, v in col_map.items()}
            df = df.rename(columns=inv_map)
            
            # Step 3: Fast Numeric Conversion
            df['tpv'] = pd.to_numeric(df['tpv'], errors='coerce', downcast='float').fillna(0)
            
            # Step 4: Filter
            targets = [t.strip().lower() for t in merchant_input.split(',') if t.strip()]
            filtered_df = df[df['receiver_name'].astype(str).str.lower().isin(targets)].copy()
            
            if not filtered_df.empty:
                # Aggregate for Table
                pivot = pd.pivot_table(filtered_df, values='tpv', index='receiver_name', 
                                       columns='pg_name', aggfunc='sum', fill_value=0)
                pivot_cr = pivot / 10_000_000
                pivot_cr['Grand Total (Cr)'] = pivot_cr.sum(axis=1)
                pivot_cr = pivot_cr.sort_values(by='Grand Total (Cr)', ascending=False)
                
                # --- STEP 5: GROUP OTHERS FOR CHART ---
                chart_df = pivot_cr.copy()
                if len(chart_df) > top_n:
                    top_merchants = chart_df.head(top_n)
                    others_row = chart_df.iloc[top_n:].sum(numeric_only=True)
                    # Create the 'Others' row as a DataFrame to keep dtypes consistent
                    others_df = pd.DataFrame([others_row], index=['Others'])
                    chart_data_final = pd.concat([top_merchants, others_df])
                else:
                    chart_data_final = chart_df

                # --- UI DISPLAY ---
                st.divider()
                m1, m2 = st.columns(2)
                m1.metric("Total Selected TPV (Cr)", f"₹{pivot_cr['Grand Total (Cr)'].sum():,.2f}")
                m2.metric("Total Records", f"{len(filtered_df):,}")
                
                tab1, tab2 = st.tabs(["📈 Market View", "📋 Detailed Data"])
                
                with tab1:
                    st.write(f"Showing Top {top_n} Merchants + Others")
                    v_df = chart_data_final.drop(columns='Grand Total (Cr)').reset_index().rename(columns={'index': 'Merchant'})
                    v_melt = v_df.melt(id_vars='Merchant', var_name='PG', value_name='Cr')
                    fig = px.bar(v_melt, x='Merchant', y='Cr', color='PG', barmode='group', template="plotly_white")
                    st.plotly_chart(fig, use_container_width=True)
                
                with tab2:
                    st.dataframe(pivot_cr.style.format("{:.2f}"), use_container_width=True)
                    csv = pivot_cr.to_csv().encode('utf-8')
                    st.download_button("📥 Download Report", data=csv, file_name="tpv_report.csv")
            else:
                st.warning("No matches found for the merchants listed.")
            
            gc.collect()

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("👋 Upload your CSV to start. The app will handle the memory and column mapping automatically.")
