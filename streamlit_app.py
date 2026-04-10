import streamlit as st
import pandas as pd
import plotly.express as px

# 1. INCREASE PANDAS STYLER LIMIT
# Setting this to match your cell count (approx 5.4 million)
pd.set_option("styler.render.max_elements", 6000000)

st.set_page_config(page_title="Instant Churn Dashboard", layout="wide")

def main():
    st.title("📊 Churn & Repeat Rate Analysis")

    uploaded_file = st.sidebar.file_uploader("Upload CSV Data", type=['csv'])

    if uploaded_file:
        try:
            # Load Data
            df = pd.read_csv(uploaded_file)
            df.columns = df.columns.str.strip()

            id_col = df.columns[0]
            filter_cols = df.columns[1:9].tolist() 
            data_cols = df.columns[9:].tolist()

            # Sidebar Filters
            st.sidebar.header("Data Filters")
            filtered_df = df.copy()
            
            for col in filter_cols:
                options = ["All"] + sorted(df[col].unique().astype(str).tolist())
                selection = st.sidebar.selectbox(f"{col}", options)
                if selection != "All":
                    filtered_df = filtered_df[filtered_df[col].astype(str) == selection]

            # KPI Metrics
            m1, m2 = st.columns(2)
            m1.metric("Selected Merchants", f"{filtered_df[id_col].nunique():,}")
            
            try:
                latest_val = pd.to_numeric(filtered_df[data_cols[-1]], errors='coerce').sum()
                m2.metric("Latest Month Activity", f"{latest_val:,.0f}")
            except:
                m2.metric("Latest Month Activity", "N/A")

            # 5. Display the Table
            st.subheader("Churn / Repeat Rate Table")
            
            # Optimization: If the dataset is still too large, we show the top 1000 
            # or allow the user to see the full filtered set.
            display_table = filtered_df[[id_col] + data_cols].set_index(id_col)

            # SAFE FORMATTER
            def safe_format(styler):
                numeric_cols = display_table.select_dtypes(include=['number']).columns
                return styler.background_gradient(cmap='YlGnBu', axis=None).format(
                    "{:.1%}", subset=numeric_cols, na_rep="0%"
                )

            # Check if filtered data is still massive to warn user
            if filtered_df.size > 5000000:
                st.warning("⚠️ Large dataset detected. Rendering may take a few seconds.")

            st.dataframe(safe_format(display_table.style), use_container_width=True)

            # 6. Trend Visualization
            st.subheader("Overall Performance Trend")
            numeric_data = filtered_df[data_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
            trend_values = numeric_data.sum().reset_index()
            trend_values.columns = ['Month', 'Value']
            
            fig = px.line(trend_values, x='Month', y='Value', markers=True)
            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.info("Please upload your base data CSV.")

if __name__ == "__main__":
    main()
