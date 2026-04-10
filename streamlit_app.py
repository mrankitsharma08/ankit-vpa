import streamlit as st
import pandas as pd
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

# Page Setup
st.set_page_config(page_title="Repeat Rate & Churn Dashboard", layout="wide")

def main():
    st.title("📊 Churn & Repeat Rate Analysis")
    st.info("Upload your CSV where Column A is the ID, B-I are Filters, and J+ are TPV months.")

    uploaded_file = st.sidebar.file_uploader("Upload Base Data CSV", type=['csv'])

    if uploaded_file:
        try:
            # 1. LOAD DATA
            df = pd.read_csv(uploaded_file)
            df.columns = df.columns.str.strip() # Clean headers
            
            # 2. DEFINE STRUCTURE BY POSITION (B to I logic)
            # Column 0: ID
            # Columns 1 to 8: Filters (B, C, D, E, F, G, H, I)
            # Columns 9 onwards: TPV Months
            id_col = df.columns[0]
            filter_cols = df.columns[1:9].tolist() 
            tpv_cols = df.columns[9:].tolist()

            # 3. TRANSFORM DATA (MELT)
            # We use indices to ensure we don't hit KeyErrors if names differ
            df_long = df.melt(
                id_vars=[id_col] + filter_cols,
                value_vars=tpv_cols,
                var_name='Month_Raw',
                value_name='TPV'
            )

            # 4. ROBUST DATE PARSING
            # Tries multiple formats common in Excel exports
            def parse_month(x):
                for fmt in ('%b-%y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%Y-%m'):
                    try:
                        return pd.to_datetime(x, format=fmt)
                    except:
                        continue
                return pd.to_datetime(x, errors='coerce')

            df_long['Month_Date'] = df_long['Month_Raw'].apply(parse_month)
            df_long['TPV'] = pd.to_numeric(df_long['TPV'], errors='coerce').fillna(0)

            # Drop rows where Month_Date failed to parse
            df_long = df_long.dropna(subset=['Month_Date'])

            # 5. SIDEBAR FILTERS
            st.sidebar.header("Dashboard Filters")
            filtered_df = df_long.copy()
            
            for col in filter_cols:
                # Get unique values, remove NaNs for the filter list
                options = ["All"] + sorted([str(x) for x in df[col].unique() if pd.notna(x)])
                selection = st.sidebar.selectbox(f"{col}", options)
                if selection != "All":
                    filtered_df = filtered_df[filtered_df[col].astype(str) == selection]

            # 6. COHORT CALCULATIONS
            # Filter for active transactions only
            active = filtered_df[filtered_df['TPV'] > 0].copy()
            
            if active.empty:
                st.warning("No data found for the selected filters (Total TPV is 0).")
                return

            # Determine Cohort (First Month of Activity)
            active['Cohort_Month'] = active.groupby(id_col)['Month_Date'].transform('min')
            
            # Calculate Month Index (0, 1, 2...)
            active['Cohort_Period'] = (
                (active['Month_Date'].dt.year - active['Cohort_Month'].dt.year) * 12 +
                (active['Month_Date'].dt.month - active['Cohort_Month'].dt.month)
            )

            # Create Pivot
            cohort_counts = active.groupby(['Cohort_Month', 'Cohort_Period'])[id_col].nunique().reset_index()
            retention_pivot = cohort_counts.pivot(index='Cohort_Month', columns='Cohort_Period', values=id_col)
            
            # Calculate Retention %
            cohort_size = retention_pivot.iloc[:, 0]
            retention_matrix = retention_pivot.divide(cohort_size, axis=0)

            # 7. DISPLAY RESULTS
            st.write(f"### Results for {filtered_df[id_col].nunique():,} Unique Merchants")
            
            tab1, tab2, tab3 = st.tabs(["Retention Heatmap", "Churn Table", "TPV Trend"])

            with tab1:
                fig, ax = plt.subplots(figsize=(12, 8))
                # Formatting the Y-axis to show Month-Year
                retention_matrix.index = retention_matrix.index.strftime('%b-%y')
                sns.heatmap(retention_matrix, annot=True, fmt=".0%", cmap="YlGnBu", ax=ax)
                plt.title("Retention Rate (%)")
                st.pyplot(fig)

            with tab2:
                churn_matrix = 1 - retention_matrix
                st.dataframe(churn_matrix.style.format("{:.1%}").background_gradient(cmap='Reds'))
                st.caption("Churn = 1 minus Retention Rate. It shows what % of the cohort stopped transacting.")

            with tab3:
                tpv_trend = filtered_df.groupby('Month_Date')['TPV'].sum().reset_index()
                fig_tpv = px.line(tpv_trend, x='Month_Date', y='TPV', title="Total TPV Trend", markers=True)
                st.plotly_chart(fig_tpv, use_container_width=True)

        except Exception as e:
            st.error(f"Critical Error: {e}")
            st.write("Troubleshooting tips:")
            st.write("- Ensure the monthly columns (J onwards) are named as dates (e.g., 'Jan-24').")
            st.write("- Check if Column A contains the Merchant/Customer ID.")
            st.write("- Make sure there are no completely empty columns between B and I.")

    else:
        st.info("Upload your CSV file to begin the analysis.")

if __name__ == "__main__":
    main()
