import streamlit as st
import pandas as pd
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt

# Set page to wide mode for better table visibility
st.set_page_config(page_title="Instant Churn Dashboard", layout="wide")

def main():
    st.title("📊 Churn & Repeat Rate Dashboard")
    st.markdown("Upload your file to instantly populate the pre-calculated metrics and filters.")

    # 1. File Uploader
    uploaded_file = st.sidebar.file_uploader("Upload CSV Data", type=['csv'])

    if uploaded_file:
        # Load data
        df = pd.read_csv(uploaded_file)
        df.columns = df.columns.str.strip() # Remove hidden spaces from headers

        # 2. Define strict mapping based on your layout
        id_col = df.columns[0]
        filter_cols = df.columns[1:9].tolist()  # B to I
        data_cols = df.columns[9:].tolist()     # J onwards (The TPV/Churn months)

        # 3. Sidebar Filters - Populated instantly
        st.sidebar.header("Data Filters")
        filtered_df = df.copy()
        
        for col in filter_cols:
            # Create a dropdown for every column from B to I
            options = ["All"] + sorted(df[col].unique().astype(str).tolist())
            selection = st.sidebar.selectbox(f"{col}", options)
            if selection != "All":
                filtered_df = filtered_df[filtered_df[col].astype(str) == selection]

        # 4. KPI Metrics - Top Row
        total_merchants = filtered_df[id_col].nunique()
        # Sum of the last available data column (Current Month)
        last_month_val = pd.to_numeric(filtered_df[data_cols[-1]], errors='coerce').sum()

        m1, m2 = st.columns(2)
        m1.metric("Selected Merchants", f"{total_merchants:,}")
        m2.metric("Latest Month Activity", f"{last_month_val:,.0f}")

        # 5. Display the Churn/Retention Table
        st.subheader("Churn / Repeat Rate Table")
        
        # Prepare the table for display (showing the filtered rows and the J+ columns)
        display_table = filtered_df[data_cols]
        
        # If your Y-axis should be the ID or a Date, we can set that as index
        # Here we use the original Index or ID
        display_table.index = filtered_df[id_col]

        # Add a heatmap style to the pre-calculated numbers
        st.dataframe(
            display_table.style.background_gradient(cmap='YlGnBu', axis=None)
            .format("{:.1%}" if display_table.max().max() <= 1 else "{:,.0f}")
        )

        # 6. Trend Visualization
        st.subheader("Overall Performance Trend")
        # Sum up all columns from J onwards to show a trend line
        trend_data = filtered_df[data_cols].sum().reset_index()
        trend_data.columns = ['Month', 'Value']
        
        fig = px.line(trend_data, x='Month', y='Value', markers=True, 
                      title="Total Performance (J to Last Column)")
        st.plotly_chart(fig, use_container_width=True)

    else:
        # Placeholder screen before upload
        st.info("Please upload your base data CSV in the sidebar to view the dashboard.")
        
        # Visual guide of what the script expects
        st.image("https://via.placeholder.com/800x200.png?text=A:ID+|+B-I:Filters+|+J-Z:Calculated+Data", use_column_width=True)

if __name__ == "__main__":
    main()
