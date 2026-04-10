import streamlit as st
import pandas as pd
import plotly.express as px

# Set page to wide mode
st.set_page_config(page_title="Instant Churn Dashboard", layout="wide")

def main():
    st.title("📊 Churn & Repeat Rate Dashboard")

    uploaded_file = st.sidebar.file_uploader("Upload CSV Data", type=['csv'])

    if uploaded_file:
        try:
            # 1. Load Data
            df = pd.read_csv(uploaded_file)
            df.columns = df.columns.str.strip() # Remove hidden spaces

            # 2. Map Columns based on your description
            # A = ID, B-I = Filters, J onwards = Data
            id_col = df.columns[0]
            filter_cols = df.columns[1:9].tolist() 
            data_cols = df.columns[9:].tolist()

            # 3. Sidebar Filters
            st.sidebar.header("Data Filters")
            filtered_df = df.copy()
            
            for col in filter_cols:
                options = ["All"] + sorted(df[col].unique().astype(str).tolist())
                selection = st.sidebar.selectbox(f"{col}", options)
                if selection != "All":
                    filtered_df = filtered_df[filtered_df[col].astype(str) == selection]

            # 4. KPI Metrics
            m1, m2 = st.columns(2)
            m1.metric("Selected Merchants", f"{filtered_df[id_col].nunique():,}")
            
            # Safe calculation for the latest month
            try:
                latest_val = pd.to_numeric(filtered_df[data_cols[-1]], errors='coerce').sum()
                m2.metric("Latest Month Activity", f"{latest_val:,.0f}")
            except:
                m2.metric("Latest Month Activity", "N/A")

            # 5. Display the Table (FIXED PORTION)
            st.subheader("Churn / Repeat Rate Table")
            
            # Select the data columns and set ID as index
            display_table = filtered_df[[id_col] + data_cols].set_index(id_col)

            # STYLER FIX: We only format numeric columns to avoid the StreamlitAPIException
            def safe_format(styler):
                # Identify columns that are numeric (float/int)
                numeric_cols = display_table.select_dtypes(include=['number']).columns
                
                # Apply percentage format ONLY to numbers between -1 and 2 (typical for churn %)
                # Apply gradient background
                return styler.background_gradient(cmap='YlGnBu', axis=None).format(
                    "{:.1%}", subset=numeric_cols, na_rep="0%"
                )

            # Render the styled dataframe
            st.dataframe(safe_format(display_table.style), use_container_width=True)

            # 6. Trend Visualization
            st.subheader("Overall Performance Trend")
            # Convert data columns to numeric for the sum calculation
            numeric_data = filtered_df[data_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
            trend_values = numeric_data.sum().reset_index()
            trend_values.columns = ['Month', 'Value']
            
            fig = px.line(trend_values, x='Month', y='Value', markers=True)
            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Error reading file structure: {e}")
            st.info("Check if Column A is ID and B-I are your 8 filters.")

    else:
        st.info("Please upload your base data CSV in the sidebar.")

if __name__ == "__main__":
    main()
