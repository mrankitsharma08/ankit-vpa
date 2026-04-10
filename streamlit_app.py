import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px

# 1. SETTINGS - Change this to your actual CSV filename
FILE_NAME = "base_data.csv" 

st.set_page_config(page_title="Repeat Rate Dashboard", layout="wide")

@st.cache_data
def load_and_process_data(file_path):
    # Load the local file
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()
    
    # Structure Identification
    id_col = df.columns[0]          # Column A: ID
    filter_cols = df.columns[1:9]   # Columns B to I: Filters
    tpv_cols = df.columns[9:]       # Columns J onwards: Monthly TPV
    
    # Transform from Wide to Long format (essential for Churn calculation)
    df_long = df.melt(
        id_vars=[id_col] + list(filter_cols),
        value_vars=list(tpv_cols),
        var_name='Month_Raw',
        value_name='TPV'
    )
    
    # Clean TPV and convert Months to actual Date objects
    df_long['TPV'] = pd.to_numeric(df_long['TPV'], errors='coerce').fillna(0)
    
    # Try common date formats found in Excel/CSV
    df_long['Month_Date'] = pd.to_datetime(df_long['Month_Raw'], errors='coerce')
    
    # Drop rows that couldn't be turned into dates (like 'Total' or 'Remarks' columns)
    df_long = df_long.dropna(subset=['Month_Date'])
    
    return df_long, list(filter_cols), id_col

def main():
    st.title("📈 Business Repeat Rate & Churn Dashboard")
    
    try:
        # Load data automatically from the local folder
        df, filter_cols, id_col = load_and_process_data(FILE_NAME)
        
        # --- SIDEBAR FILTERS ---
        st.sidebar.header("Filter Controls")
        filtered_df = df.copy()
        
        # Create dynamic dropdowns for every filter column (B to I)
        for col in filter_cols:
            options = ["All"] + sorted(df[col].unique().astype(str).tolist())
            choice = st.sidebar.selectbox(f"Filter by {col}", options)
            if choice != "All":
                filtered_df = filtered_df[filtered_df[col].astype(str) == choice]

        # --- DYNAMIC CALCULATION ---
        # 1. Identify "Active" users (TPV > 0)
        active = filtered_df[filtered_df['TPV'] > 0].copy()
        
        # 2. Assign Cohort (The very first month a customer had TPV > 0)
        active['Cohort'] = active.groupby(id_col)['Month_Date'].transform('min')
        
        # 3. Calculate Period (Month 0, Month 1, etc.)
        active['Period'] = (
            (active['Month_Date'].dt.year - active['Cohort'].dt.year) * 12 +
            (active['Month_Date'].dt.month - active['Cohort'].dt.month)
        )
        
        # 4. Create Retention Matrix
        cohort_counts = active.groupby(['Cohort', 'Period'])[id_col].nunique().reset_index()
        retention_pivot = cohort_counts.pivot(index='Cohort', columns='Period', values=id_col)
        retention_matrix = retention_pivot.divide(retention_pivot.iloc[:, 0], axis=0)

        # --- UI LAYOUT ---
        m1, m2, m3 = st.columns(3)
        m1.metric("Unique IDs", f"{filtered_df[id_col].nunique():,}")
        m2.metric("Total TPV", f"{filtered_df['TPV'].sum():,.0f}")
        m3.metric("Selected Filter Rows", f"{len(filtered_df):,}")

        st.subheader("Retention & Churn Heatmap")
        st.info("This table updates instantly when you change filters in the sidebar.")
        
        # Plot Heatmap
        fig, ax = plt.subplots(figsize=(12, 7))
        # Format the Y-axis to readable Month-Year
        retention_matrix.index = retention_matrix.index.strftime('%b-%Y')
        sns.heatmap(retention_matrix, annot=True, fmt=".0%", cmap="YlGnBu", ax=ax)
        plt.title("Retention Rate % (Month 0 = Month Joined)")
        st.pyplot(fig)

        # Toggle to Churn View
        if st.checkbox("Show Churn Rate instead (1 - Retention)"):
            st.write("### Churn Rate Table")
            churn_matrix = 1 - retention_matrix
            st.dataframe(churn_matrix.style.format("{:.1%}").background_gradient(cmap='Reds'))
        else:
            st.write("### Raw Retention Data")
            st.dataframe(retention_matrix.style.format("{:.1%}"))

    except FileNotFoundError:
        st.error(f"File '{FILE_NAME}' not found. Please ensure your CSV is in the same folder as this script.")
    except Exception as e:
        st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
