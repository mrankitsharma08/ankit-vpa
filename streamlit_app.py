import streamlit as st
import pandas as pd
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt

st.set_page_config(page_title="Churn Dashboard", layout="wide")

def main():
    st.title("📊 Churn & Repeat Rate Analysis")
    
    uploaded_file = st.sidebar.file_uploader("Upload your Base Data CSV", type=['csv'])
    
    if uploaded_file:
        # Load raw data first to inspect
        df_raw = pd.read_csv(uploaded_file)
        df_raw.columns = df_raw.columns.str.strip() # Remove hidden spaces
        
        st.write("### 🔍 Data Preview (First 5 rows)")
        st.dataframe(df_raw.head())

        # --- DYNAMIC COLUMN DETECTION ---
        # 1. ID Column (Column A)
        id_col = df_raw.columns[0]
        
        # 2. Filter Columns (Looking for your specific names)
        potential_filters = [
            'Business Category', 'Business Super Category', 'PG & PL', 
            'Deactivated Segmant', 'Platform / Reseller', 'Blocked'
        ]
        found_filters = [c for c in potential_filters if c in df_raw.columns]
        
        # 3. TPV Columns (Everything else that isn't a filter or the ID)
        # Usually, these are the columns starting from the 10th position
        tpv_cols = [c for c in df_raw.columns if c not in found_filters and c != id_col]

        st.sidebar.success(f"Detected {len(tpv_cols)} monthly TPV columns.")

        try:
            # --- TRANSFORMATION (MELT) ---
            df_long = df_raw.melt(
                id_vars=[id_col] + found_filters,
                value_vars=tpv_cols,
                var_name='Month_Name',
                value_name='TPV'
            )
            
            # Convert values
            df_long['TPV'] = pd.to_numeric(df_long['TPV'], errors='coerce').fillna(0)
            df_long['Month_Date'] = pd.to_datetime(df_long['Month_Name'], errors='ignore')

            # --- SIDEBAR FILTERS ---
            st.sidebar.header("Global Filters")
            filtered_df = df_long.copy()
            for col in found_filters:
                options = ["All"] + sorted(list(df_raw[col].unique().astype(str)))
                selection = st.sidebar.selectbox(f"Filter {col}", options)
                if selection != "All":
                    filtered_df = filtered_df[filtered_df[col] == selection]

            # --- CALCULATE CHURN ---
            active = filtered_df[filtered_df['TPV'] > 0].copy()
            if active.empty:
                st.warning("No active customers found (TPV > 0) with the current filters.")
                return

            # Cohort = First month with TPV > 0
            active['Cohort'] = active.groupby(id_col)['Month_Date'].transform('min')
            active['Period'] = ((active['Month_Date'].dt.year - active['Cohort'].dt.year) * 12 + 
                                (active['Month_Date'].dt.month - active['Cohort'].dt.month))
            
            # Pivot & Retention
            pivot = active.groupby(['Cohort', 'Period']).agg(n=(id_col, 'nunique')).reset_index()
            retention_pivot = pivot.pivot(index='Cohort', columns='Period', values='n')
            retention_matrix = retention_pivot.divide(retention_pivot.iloc[:, 0], axis=0)

            # --- VISUALS ---
            c1, c2 = st.columns([3, 1])
            with c1:
                st.subheader("Retention Heatmap")
                fig, ax = plt.subplots(figsize=(10, 6))
                sns.heatmap(retention_matrix, annot=True, fmt=".0%", cmap="YlGnBu")
                st.pyplot(fig)
            
            with c2:
                st.subheader("Churn Table")
                churn_matrix = 1 - retention_matrix
                st.dataframe(churn_matrix.style.format("{:.0%}").background_gradient(cmap='Reds'))

            st.subheader("TPV Performance")
            tpv_trend = filtered_df.groupby('Month_Name')['TPV'].sum().reset_index()
            st.plotly_chart(px.line(tpv_trend, x='Month_Name', y='TPV'))

        except Exception as e:
            st.error(f"Error during calculation: {e}")
            st.info("Check if your Month columns (TPV) are named correctly (e.g., 'Jan-24' or '2024-01-01').")
    else:
        st.info("Please upload your CSV file.")

if __name__ == "__main__":
    main()
