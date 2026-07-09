import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", page_title="Excel-like Data Analyzer")
st.title("📊 VPA Data Analyzer")

# 1. File Uploader
uploaded_file = st.file_uploader("Upload your CSV or Excel file", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        # Automatically detect format type and read headers dynamically
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        st.success("File uploaded successfully!")
        
        # Grid/Tabs Layout
        tab1, tab2 = st.tabs(["🔍 Data Viewer & Advanced Filters", "🧮 Pivot Table Builder"])
        
        with tab1:
            st.subheader("Filter and Search Data")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                filter_col = st.selectbox("Select column to filter by", options=["None"] + list(df.columns))
            
            filtered_df = df.copy()
            
            if filter_col != "None":
                is_numeric = pd.api.types.is_numeric_dtype(df[filter_col])
                
                if is_numeric:
                    with col2:
                        condition = st.selectbox("Condition", ["Equal to", "Greater than", "Less than", "Between"])
                    with col3:
                        if condition == "Between":
                            min_val = float(df[filter_col].min())
                            max_val = float(df[filter_col].max())
                            val = st.slider("Select Range", min_val, max_val, (min_val, max_val))
                            filtered_df = df[(df[filter_col] >= val[0]) & (df[filter_col] <= val[1])]
                        else:
                            val = st.number_input("Enter value", value=float(df[filter_col].mean()))
                            if condition == "Equal to": filtered_df = df[df[filter_col] == val]
                            elif condition == "Greater than": filtered_df = df[df[filter_col] > val]
                            elif condition == "Less than": filtered_df = df[df[filter_col] < val]
                else:
                    with col2:
                        condition = st.selectbox("Condition", ["Contains", "Equals", "Begins with", "Ends with"])
                    with col3:
                        search_text = st.text_input("Search text").strip()
                        
                    if search_text:
                        if condition == "Contains":
                            filtered_df = df[df[filter_col].astype(str).str.contains(search_text, case=False, na=False)]
                        elif condition == "Equals":
                            filtered_df = df[df[filter_col].astype(str).str.lower() == search_text.lower()]
                        elif condition == "Begins with":
                            filtered_df = df[df[filter_col].astype(str).str.lower().str.startswith(search_text.lower(), na=False)]
                        elif condition == "Ends with":
                            filtered_df = df[df[filter_col].astype(str).str.lower().str.endswith(search_text.lower(), na=False)]

            st.metric(label="Rows Found", value=len(filtered_df))
            st.dataframe(filtered_df, use_container_width=True)
            
        with tab2:
            st.subheader("Create a Pivot Table")
            p_col1, p_col2, p_col3, p_col4 = st.columns(4)
            
            with p_col1:
                pivot_index = st.multiselect("Rows (Index)", options=df.columns)
            with p_col2:
                pivot_columns = st.multiselect("Columns", options=df.columns)
            with p_col3:
                num_cols = df.select_dtypes(include=['number']).columns.tolist()
                pivot_values = st.multiselect("Values (Numeric only)", options=num_cols)
            with p_col4:
                agg_func = st.selectbox("Aggregation Function", ["sum", "mean", "count", "min", "max"])
                
            if pivot_index and pivot_values:
                try:
                    pivot_table = df.pivot_table(
                        index=pivot_index,
                        columns=pivot_columns if pivot_columns else None,
                        values=pivot_values,
                        aggfunc=agg_func,
                        fill_value=0
                    )
                    st.markdown("### 📋 Resulting Pivot Table")
                    st.dataframe(pivot_table, use_container_width=True)
                except Exception as e:
                    st.error(f"Could not generate pivot table: {e}")
            else:
                st.info("To build a pivot table, please select at least one **Row** and one **Value** column.")
                
    except Exception as e:
        st.error(f"Error reading file: {e}")
else:
    st.info("Please upload a CSV or Excel file to get started.")
