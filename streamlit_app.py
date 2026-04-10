import streamlit as st
import pandas as pd
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt

# Page configuration
st.set_page_config(page_title="Churn & Repeat Rate Dashboard", layout="wide")

@st.cache_data
def process_data(file):
    # Read CSV
    df = pd.read_csv(file)
    
    # 1. Clean column names to prevent KeyError from hidden spaces
    df.columns = df.columns.str.strip()
    
    # 2. Identify ID column (Column A)
    id_col = df.columns[0]
    
    # 3. Define the filter columns provided (B to I)
    # Using a list that matches your description
    potential_filters = [
        'Business Category', 
        'Business Super Category', 
        'PG & PL', 
        'Deactivated Segmant', 
        'Platform / Reseller', 
        'Blocked'
    ]
    
    # Check which filters actually exist in the file to avoid crashing
    filters = [c for c in potential_filters if c in df.columns]
    
    # 4. Identify TPV columns (The rest of the columns from index 9 onwards)
    # If B-I are metadata, TPV columns usually start at the 10th column
    tpv_cols = df.columns[9:].tolist()
    
    # 5. Transform Wide data to Long data (Melt)
    # This is where the KeyError happened; now we use the verified 'filters' list
    df_long = df.melt(
        id_vars=[id_col] + filters,
        value_vars=tpv_cols,
        var_name='Month_Name',
        value_name='TPV'
    )
    
    # Convert TPV to numeric and Month to datetime for sorting
    df_long['TPV'] = pd.to_numeric(df_long['TPV'], errors='coerce').fillna(0)
    df_long['Month_Date'] = pd.to_datetime(df_long['Month_Name'], errors='ignore')
    
    return df_long, filters, id_col

def main():
    st.title("📊 Churn & Repeat Rate Analysis")
    st.markdown("---")
    
    uploaded_file = st.sidebar.file_uploader("Upload your Base Data CSV", type=['csv'])
    
    if uploaded_file:
        try:
            df, filter_cols, id_col = process_data(uploaded_file)
            
            # --- SIDEBAR FILTERS ---
            st.sidebar.header("Global Filters")
            filtered_df = df.copy()
            
            for col in filter_cols:
                options = ["All"] + sorted(list(df[col].unique().astype(str)))
                selection = st.sidebar.selectbox(f"Filter {col}", options)
                if selection != "All":
                    filtered_df = filtered_df[filtered_df[col] == selection]

            # --- CALCULATE CHURN / RETENTION ---
            # Define active as TPV > 0
            active = filtered_df[filtered_df['TPV'] > 0].copy()
            
            # Get Cohort Month (First month with TPV > 0)
            active['Cohort'] = active.groupby(id_col)['Month_Date'].transform('min')
            
            # Calculate Month Index (0, 1, 2...)
            active['Period'] = ((active['Month_Date'].dt.year - active['Cohort'].dt.year) * 12 + 
                                (active['Month_Date'].dt.month - active['Cohort'].dt.month))
            
            # Create Pivot Table
            cohort_pivot = active.groupby(['Cohort', 'Period']).agg(n_customers=(id_col, 'nunique')).reset_index()
            pivot = cohort_pivot.pivot(index='Cohort', columns='Period', values='n_customers')
            
            # Calculate Retention Rate
            cohort_size = pivot.iloc[:, 0]
            retention_matrix = pivot.divide(cohort_size, axis=0)
            
            # --- DASHBOARD UI ---
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.subheader("Retention Heatmap")
                fig, ax = plt.subplots(figsize=(10, 6))
                sns.heatmap(retention_matrix, annot=True, fmt=".0%", cmap="YlGnBu", ax=ax)
                plt.xlabel("Months Since First Transaction")
                plt.ylabel("Cohort Month")
                st.pyplot(fig)
                
            with col2:
                st.subheader("Summary Metrics")
                st.metric("Total Customers (Filtered)", f"{filtered_df[id_col].nunique():,}")
                st.metric("Current Month TPV", f"{filtered_df[filtered_df['Month_Date'] == filtered_df['Month_Date'].max()]['TPV'].sum():,.0f}")
                
            st.markdown("---")
            
            # Churn Table View
            st.subheader("Churn Rate Table (1 - Retention)")
            churn_matrix = 1 - retention_matrix
            st.dataframe(churn_matrix.style.format("{:.1%").background_gradient(cmap='Reds'))
            
            # TPV Trend
            st.subheader("Total TPV Trend")
            tpv_trend = filtered_df.groupby('Month_Date')['TPV'].sum().reset_index()
            fig_line = px.line(tpv_trend, x='Month_Date', y='TPV', markers=True)
            st.plotly_chart(fig_line, use_container_width=True)

        except Exception as e:
            st.error(f"Error processing data: {e}")
            st.info("Check if your CSV headers match the requested format.")
            
    else:
        st.info("👋 Please upload your base data CSV in the sidebar to begin.")

if __name__ == "__main__":
    main()
