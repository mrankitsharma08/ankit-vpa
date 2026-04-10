import streamlit as st
import pandas as pd
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt

# Set page layout
st.set_page_config(page_title="Churn & Retention Dashboard", layout="wide")

@st.cache_data
def load_data(file):
    df = pd.read_csv(file)
    # Attempt to convert date columns automatically
    for col in df.columns:
        if 'date' in col.lower() or 'month' in col.lower():
            try:
                df[col] = pd.to_datetime(df[col])
            except:
                pass
    return df

def generate_cohort_table(df, id_col, date_col):
    """Generates a standard Cohort Retention/Churn table."""
    # Create Cohort (First purchase month)
    df['OrderMonth'] = df[date_col].dt.to_period('M')
    df['Cohort'] = df.groupby(id_col)[date_col].transform('min').dt.to_period('M')
    
    # Calculate periods between purchases
    df_cohort = df.groupby(['Cohort', 'OrderMonth']).agg(n_customers=(id_col, 'nunique')).reset_index()
    df_cohort['period_number'] = (df_cohort.OrderMonth - df_cohort.Cohort).apply(lambda r: r.n)
    
    # Pivot for the matrix
    cohort_pivot = df_cohort.pivot_table(index='Cohort', columns='period_number', values='n_customers')
    
    # Convert to percentages (Retention Rate)
    cohort_size = cohort_pivot.iloc[:, 0]
    retention_matrix = cohort_pivot.divide(cohort_size, axis=0)
    return retention_matrix

def main():
    st.title("📊 Customer Churn Dashboard")
    
    # 1. Upload Section
    uploaded_file = st.sidebar.file_uploader("Upload your CSV Base Data", type=['csv'])
    
    if uploaded_file is not None:
        df = load_data(uploaded_file)
        
        # 2. Sidebar Filters
        st.sidebar.header("Filter Data")
        # Let user pick the ID and Date columns if not auto-detected
        id_col = st.sidebar.selectbox("Select Customer ID Column", df.columns)
        date_col = st.sidebar.selectbox("Select Transaction Date Column", df.columns)
        
        # Dynamic Category Filters (for columns with low cardinality)
        cat_cols = [col for col in df.columns if df[col].nunique() < 20 and col not in [id_col, date_col]]
        for col in cat_cols:
            options = ["All"] + list(df[col].unique())
            selection = st.sidebar.selectbox(f"Filter by {col}", options)
            if selection != "All":
                df = df[df[col] == selection]

        # 3. Key Metrics
        total_cust = df[id_col].nunique()
        total_rev = df['Revenue'].sum() if 'Revenue' in df.columns else "N/A"
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Unique Customers", f"{total_cust:,}")
        m2.metric("Total Rows", f"{len(df):,}")
        m3.metric("Total Value", f"{total_rev}")

        # 4. Churn / Retention Table
        st.subheader("Retention Matrix (Cohort Analysis)")
        try:
            retention = generate_cohort_table(df, id_col, date_col)
            
            # Plotting the Heatmap
            fig, ax = plt.subplots(figsize=(12, 8))
            sns.heatmap(retention, annot=True, fmt=".0%", cmap="YlGnBu", ax=ax)
            plt.title("Retention Rate by Cohort")
            st.pyplot(fig)
            
            # Show the inverse (Churn)
            if st.checkbox("Show as Churn Rate (1 - Retention)"):
                churn_matrix = 1 - retention
                st.dataframe(churn_matrix.style.format("{:.1%}").background_gradient(cmap='Reds'))
            else:
                st.dataframe(retention.style.format("{:.1%}"))
                
        except Exception as e:
            st.error(f"Could not generate cohort table. Ensure your date column is valid. Error: {e}")

        # 5. Trend Analysis
        st.subheader("Customer Growth Trend")
        df['Month'] = df[date_col].dt.to_period('M').astype(str)
        trend = df.groupby('Month')[id_col].nunique().reset_index()
        fig_trend = px.line(trend, x='Month', y=id_col, title="Monthly Active Customers")
        st.plotly_chart(fig_trend, use_container_width=True)

    else:
        st.info("Please upload a CSV file to begin.")

if __name__ == "__main__":
    main()
