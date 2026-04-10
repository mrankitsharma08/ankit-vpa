import streamlit as st
import pandas as pd
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt

st.set_page_config(page_title="Repeat Rate Dashboard", layout="wide")

@st.cache_data
def process_data(file):
    df = pd.read_csv(file)
    
    # 1. Identify Filter Columns (B to I - assuming these are the first 7-9 columns)
    # Based on your list: Business Category, Super Category, PG & PL, Deactivated, Platform, Blocked
    filter_columns = [
        'Business Category', 'Business Super Category', 'PG & PL', 
        'Deactivated Segmant', 'Platform / Reseller', 'Blocked'
    ]
    
    # Identify TPV columns (The rest of the columns)
    # We assume 'Customer ID' or similar is column A (index 0)
    all_cols = df.columns.tolist()
    tpv_columns = [c for c in all_cols if c not in filter_columns and c != all_cols[0]]
    id_col = all_cols[0] 

    # 2. Melt the data (Wide to Long)
    # This turns months from columns into rows so we can calculate churn
    df_long = df.melt(
        id_vars=[id_col] + filter_columns,
        value_vars=tpv_columns,
        var_name='Month',
        value_name='TPV'
    )
    
    # Clean TPV and Dates
    df_long['TPV'] = pd.to_numeric(df_long['TPV'], errors='coerce').fillna(0)
    df_long['Month'] = pd.to_datetime(df_long['Month'], errors='ignore')
    
    return df_long, filter_columns, id_col

def main():
    st.title("📊 Churn & Repeat Rate Analysis")
    
    uploaded_file = st.sidebar.file_uploader("Upload Base Data CSV", type=['csv'])
    
    if uploaded_file:
        df, filters, id_col = process_data(uploaded_file)
        
        # --- SIDEBAR FILTERS ---
        st.sidebar.header("Dashboard Filters")
        filtered_df = df.copy()
        
        for col in filters:
            if col in df.columns:
                options = ["All"] + sorted(list(df[col].unique().astype(str)))
                selection = st.sidebar.selectbox(f"{col}", options)
                if selection != "All":
                    filtered_df = filtered_df[filtered_df[col] == selection]

        # --- CHURN CALCULATION ---
        # A user is "Active" if TPV > 0
        active_users = filtered_df[filtered_df['TPV'] > 0]
        
        # Create Cohorts (Month of first TPV > 0)
        active_users['Cohort'] = active_users.groupby(id_col)['Month'].transform('min')
        
        # Calculate Retention
        cohort_data = active_users.groupby(['Cohort', 'Month']).agg(users=(id_col, 'nunique')).reset_index()
        # Convert months to strings for better pivoting
        cohort_data['Cohort_Str'] = cohort_data['Cohort'].dt.strftime('%Y-%m')
        cohort_data['Month_Str'] = cohort_data['Month'].dt.strftime('%Y-%m')
        
        # Calculate period number (0 = Month of joining, 1 = Next month...)
        cohort_data['Period'] = ((cohort_data['Month'].dt.year - cohort_data['Cohort'].dt.year) * 12 + 
                                 (cohort_data['Month'].dt.month - cohort_data['Cohort'].dt.month))

        retention_pivot = cohort_data.pivot_table(index='Cohort_Str', columns='Period', values='users')
        retention_rate = retention_pivot.divide(retention_pivot.iloc[:, 0], axis=0)

        # --- VISUALIZATION ---
        m1, m2 = st.columns([2, 1])
        
        with m1:
            st.subheader("Retention Heatmap (%)")
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.heatmap(retention_rate, annot=True, fmt=".0%", cmap="YlGnBu", ax=ax)
            st.pyplot(fig)

        with m2:
            st.subheader("Churn Table")
            churn_rate = 1 - retention_rate
            st.dataframe(churn_rate.style.format("{:.1%").background_gradient(cmap='Reds'))

        # --- TPV ANALYSIS ---
        st.subheader("TPV Trend by Filtered Segment")
        tpv_trend = filtered_df.groupby('Month')['TPV'].sum().reset_index()
        fig_tpv = px.area(tpv_trend, x='Month', y='TPV', title="Total TPV Over Time")
        st.plotly_chart(fig_tpv, use_container_width=True)

if __name__ == "__main__":
    main()
