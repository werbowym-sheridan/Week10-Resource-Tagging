import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
from datetime import datetime
import os

st.set_page_config(page_title="Week 10: Resource Tagging Cost Governance", layout="wide")

@st.cache_data
def load_cloudmart_data(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Remove quotes from each line and split by comma
    clean_lines = []
    for line in lines:
        clean_line = line.strip().strip('"')
        clean_lines.append(clean_line)

    # Create a temporary clean file content
    clean_content = '\n'.join(clean_lines)

    # Read as CSV from string
    from io import StringIO
    df = pd.read_csv(StringIO(clean_content))
    return df

@st.cache_data
def calculate_tag_completeness_score(df):
    tag_columns = ['Department', 'Project', 'Environment', 'Owner', 'CostCenter']

    df_copy = df.copy()
    df_copy['TagCompleteness'] = 0

    for col in tag_columns:
        df_copy['TagCompleteness'] += (~df_copy[col].isna() & (df_copy[col] != '')).astype(int)

    df_copy['TagCompletenessPercentage'] = (df_copy['TagCompleteness'] / len(tag_columns)) * 100

    return df_copy

@st.cache_data
def analyze_data_exploration(df):
    results = {}
    results['shape'] = df.shape
    results['missing_values'] = df.isnull().sum()
    results['tagged_counts'] = df['Tagged'].value_counts()
    results['untagged_percentage'] = (results['tagged_counts'].get('No', 0) / len(df)) * 100

    return results

@st.cache_data
def analyze_cost_visibility(df):
    results = {}

    cost_by_tagging = df.groupby('Tagged')['MonthlyCostUSD'].sum()
    results['tagged_cost'] = cost_by_tagging.get('Yes', 0)
    results['untagged_cost'] = cost_by_tagging.get('No', 0)
    results['total_cost'] = results['tagged_cost'] + results['untagged_cost']
    results['untagged_cost_percentage'] = (results['untagged_cost'] / results['total_cost']) * 100 if results['total_cost'] > 0 else 0

    dept_tagging = df.groupby(['Department', 'Tagged'])['MonthlyCostUSD'].sum().reset_index()
    untagged_by_dept = dept_tagging[dept_tagging['Tagged'] == 'No'].sort_values('MonthlyCostUSD', ascending=False)
    results['untagged_by_department'] = untagged_by_dept

    project_cost = df.groupby('Project')['MonthlyCostUSD'].sum().sort_values(ascending=False).reset_index()
    results['project_costs'] = project_cost

    env_tagging = df.groupby(['Environment', 'Tagged'])['MonthlyCostUSD'].sum().reset_index()
    results['environment_analysis'] = env_tagging

    return results

@st.cache_data
def analyze_tagging_compliance(df):
    results = {}

    df_with_scores = calculate_tag_completeness_score(df)
    results['completeness_data'] = df_with_scores

    lowest_scores = df_with_scores.nsmallest(5, 'TagCompletenessPercentage')[['ResourceID', 'Service', 'TagCompletenessPercentage', 'MonthlyCostUSD']]
    results['lowest_completeness'] = lowest_scores

    tag_columns = ['Department', 'Project', 'Environment', 'Owner', 'CostCenter']
    missing_counts = {}
    for col in tag_columns:
        missing_counts[col] = df[col].isna().sum() + (df[col] == '').sum()
    results['missing_fields'] = missing_counts

    untagged_resources = df[df['Tagged'] == 'No'][['ResourceID', 'Service', 'Department', 'MonthlyCostUSD']].sort_values('MonthlyCostUSD', ascending=False)
    results['untagged_resources'] = untagged_resources

    return results

st.title("🏷️ Week 10: CloudMart Resource Tagging Cost Governance")
st.markdown("**Analyzing resource tagging compliance and cost visibility for CloudMart Inc.**")

file_path = "original.csv"

if 'cloudmart_data' not in st.session_state:
    st.session_state.cloudmart_data = load_cloudmart_data(file_path)

if 'remediated_data' not in st.session_state:
    st.session_state.remediated_data = st.session_state.cloudmart_data.copy()

df = st.session_state.cloudmart_data
remediated_df = st.session_state.remediated_data

st.success(f"✅ CloudMart data loaded! {len(df)} resources across {df['AccountID'].nunique()} accounts")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Data Exploration", "💰 Cost Visibility", "📝 Tagging Compliance", "📈 Visualizations", "🔧 Tag Remediation"])

with tab1:
    st.subheader("📊 Task Set 1: Data Exploration")

    exploration_results = analyze_data_exploration(df)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Dataset Overview")
        st.write(f"**Shape:** {exploration_results['shape'][0]} rows, {exploration_results['shape'][1]} columns")
        st.dataframe(df.head())

        st.markdown("### Missing Values Analysis")
        missing_df = pd.DataFrame({
            'Column': exploration_results['missing_values'].index,
            'Missing Count': exploration_results['missing_values'].values
        }).sort_values('Missing Count', ascending=False)
        st.dataframe(missing_df)

    with col2:
        st.markdown("### Tagging Status")
        tagged_counts = exploration_results['tagged_counts']

        st.metric("Total Resources", len(df))
        st.metric("Tagged Resources", tagged_counts.get('Yes', 0))
        st.metric("Untagged Resources", tagged_counts.get('No', 0))
        st.metric("Untagged Percentage", f"{exploration_results['untagged_percentage']:.1f}%")

        fig_pie = px.pie(
            values=tagged_counts.values,
            names=tagged_counts.index,
            title="Resource Tagging Status Distribution",
            color_discrete_map={'Yes': 'green', 'No': 'red'}
        )
        st.plotly_chart(fig_pie, use_container_width=True)

with tab2:
    st.subheader("💰 Task Set 2: Cost Visibility")

    cost_results = analyze_cost_visibility(df)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Cost Summary")
        st.metric("Total Monthly Cost", f"${cost_results['total_cost']:,.2f}")
        st.metric("Tagged Resources Cost", f"${cost_results['tagged_cost']:,.2f}")
        st.metric("Untagged Resources Cost", f"${cost_results['untagged_cost']:,.2f}")
        st.metric("Untagged Cost Percentage", f"{cost_results['untagged_cost_percentage']:.1f}%")

        st.markdown("### Top Projects by Cost")
        st.dataframe(cost_results['project_costs'].head(10))

    with col2:
        st.markdown("### Untagged Cost by Department")
        if not cost_results['untagged_by_department'].empty:
            fig_dept = px.bar(
                cost_results['untagged_by_department'].head(10),
                x='Department',
                y='MonthlyCostUSD',
                title="Untagged Cost by Department",
                color='MonthlyCostUSD',
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_dept, use_container_width=True)

        st.markdown("### Environment Cost Analysis")
        env_pivot = cost_results['environment_analysis'].pivot(index='Environment', columns='Tagged', values='MonthlyCostUSD').fillna(0)
        fig_env = px.bar(
            env_pivot.reset_index(),
            x='Environment',
            y=['Yes', 'No'],
            title="Cost by Environment and Tagging Status",
            barmode='group',
            color_discrete_map={'Yes': 'green', 'No': 'red'}
        )
        st.plotly_chart(fig_env, use_container_width=True)

with tab3:
    st.subheader("📝 Task Set 3: Tagging Compliance")

    compliance_results = analyze_tagging_compliance(df)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Tag Completeness Analysis")
        st.write("**Top 5 Resources with Lowest Completeness Scores:**")
        st.dataframe(compliance_results['lowest_completeness'])

        st.markdown("### Missing Tag Fields")
        missing_fields_df = pd.DataFrame({
            'Tag Field': list(compliance_results['missing_fields'].keys()),
            'Missing Count': list(compliance_results['missing_fields'].values())
        }).sort_values('Missing Count', ascending=False)

        fig_missing = px.bar(
            missing_fields_df,
            x='Tag Field',
            y='Missing Count',
            title="Most Frequently Missing Tag Fields"
        )
        st.plotly_chart(fig_missing, use_container_width=True)

    with col2:
        st.markdown("### Untagged Resources")
        st.write(f"**{len(compliance_results['untagged_resources'])} untagged resources found:**")
        st.dataframe(compliance_results['untagged_resources'].head(10))

        csv_untagged = compliance_results['untagged_resources'].to_csv(index=False)
        st.download_button(
            label="📥 Download Untagged Resources CSV",
            data=csv_untagged,
            file_name="untagged_resources.csv",
            mime="text/csv"
        )

        completeness_dist = compliance_results['completeness_data']['TagCompletenessPercentage']
        fig_completeness = px.histogram(
            x=completeness_dist,
            nbins=6,
            title="Tag Completeness Score Distribution",
            labels={'x': 'Completeness Percentage', 'y': 'Number of Resources'}
        )
        st.plotly_chart(fig_completeness, use_container_width=True)

with tab4:
    st.subheader("📈 Task Set 4: Visualization Dashboard")

    col1, col2, col3 = st.columns(3)

    with col1:
        service_filter = st.multiselect("Filter by Service", df['Service'].unique(), default=df['Service'].unique())
        region_filter = st.multiselect("Filter by Region", df['Region'].unique(), default=df['Region'].unique())

    with col2:
        department_filter = st.multiselect("Filter by Department", df['Department'].dropna().unique(), default=df['Department'].dropna().unique())
        environment_filter = st.multiselect("Filter by Environment", df['Environment'].dropna().unique(), default=df['Environment'].dropna().unique())

    with col3:
        project_filter = st.multiselect("Filter by Project", df['Project'].dropna().unique(), default=df['Project'].dropna().unique())

    filtered_df = df[
        (df['Service'].isin(service_filter)) &
        (df['Region'].isin(region_filter)) &
        (df['Department'].isin(department_filter) | df['Department'].isna()) &
        (df['Environment'].isin(environment_filter) | df['Environment'].isna()) &
        (df['Project'].isin(project_filter) | df['Project'].isna())
    ]

    st.write(f"Showing {len(filtered_df)} resources after filtering")

    col1, col2 = st.columns(2)

    with col1:
        dept_tag_analysis = filtered_df.groupby(['Department', 'Tagged'])['MonthlyCostUSD'].sum().reset_index()
        fig_dept_tag = px.bar(
            dept_tag_analysis,
            x='Department',
            y='MonthlyCostUSD',
            color='Tagged',
            title="Cost per Department by Tagging Status",
            barmode='group',
            color_discrete_map={'Yes': 'green', 'No': 'red'}
        )
        fig_dept_tag.update_xaxes(tickangle=45)
        st.plotly_chart(fig_dept_tag, use_container_width=True)

        service_cost = filtered_df.groupby('Service')['MonthlyCostUSD'].sum().sort_values(ascending=True)
        fig_service = px.bar(
            x=service_cost.values,
            y=service_cost.index,
            orientation='h',
            title="Total Cost per Service",
            labels={'x': 'Monthly Cost USD', 'y': 'Service'}
        )
        st.plotly_chart(fig_service, use_container_width=True)

    with col2:
        env_cost = filtered_df.groupby('Environment')['MonthlyCostUSD'].sum()
        fig_env_pie = px.pie(
            values=env_cost.values,
            names=env_cost.index,
            title="Cost Distribution by Environment"
        )
        st.plotly_chart(fig_env_pie, use_container_width=True)

        account_analysis = filtered_df.groupby(['AccountID', 'Tagged'])['MonthlyCostUSD'].sum().reset_index()
        fig_account = px.bar(
            account_analysis,
            x='AccountID',
            y='MonthlyCostUSD',
            color='Tagged',
            title="Cost per Account by Tagging Status",
            barmode='group',
            color_discrete_map={'Yes': 'green', 'No': 'red'}
        )
        st.plotly_chart(fig_account, use_container_width=True)

with tab5:
    st.subheader("🔧 Task Set 5: Tag Remediation Workflow")

    st.markdown("### Interactive Tag Remediation")
    st.write("Edit untagged resources to improve tagging compliance:")

    untagged_for_editing = remediated_df[remediated_df['Tagged'] == 'No'].copy()

    if not untagged_for_editing.empty:
        edited_df = st.data_editor(
            untagged_for_editing[['ResourceID', 'Service', 'Department', 'Project', 'Environment', 'Owner', 'CostCenter', 'MonthlyCostUSD']],
            num_rows="dynamic",
            use_container_width=True,
            key="remediation_editor"
        )

        if st.button("💾 Apply Remediation"):
            for idx, row in edited_df.iterrows():
                resource_id = row['ResourceID']
                mask = remediated_df['ResourceID'] == resource_id

                remediated_df.loc[mask, 'Department'] = row['Department']
                remediated_df.loc[mask, 'Project'] = row['Project']
                remediated_df.loc[mask, 'Environment'] = row['Environment']
                remediated_df.loc[mask, 'Owner'] = row['Owner']
                remediated_df.loc[mask, 'CostCenter'] = row['CostCenter']

                if not pd.isna(row['Department']) and not pd.isna(row['Project']):
                    remediated_df.loc[mask, 'Tagged'] = 'Yes'

            st.session_state.remediated_data = remediated_df
            st.success("✅ Remediation applied successfully!")
            st.rerun()

    else:
        st.success("🎉 All resources are properly tagged!")

    st.markdown("### Before vs After Comparison")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Original Data")
        original_tagged = (df['Tagged'] == 'Yes').sum()
        original_untagged = (df['Tagged'] == 'No').sum()
        original_untagged_cost = df[df['Tagged'] == 'No']['MonthlyCostUSD'].sum()

        st.metric("Tagged Resources", original_tagged)
        st.metric("Untagged Resources", original_untagged)
        st.metric("Untagged Cost", f"${original_untagged_cost:,.2f}")

    with col2:
        st.markdown("#### After Remediation")
        remediated_tagged = (remediated_df['Tagged'] == 'Yes').sum()
        remediated_untagged = (remediated_df['Tagged'] == 'No').sum()
        remediated_untagged_cost = remediated_df[remediated_df['Tagged'] == 'No']['MonthlyCostUSD'].sum()

        st.metric("Tagged Resources", remediated_tagged, delta=remediated_tagged - original_tagged)
        st.metric("Untagged Resources", remediated_untagged, delta=remediated_untagged - original_untagged)
        st.metric("Untagged Cost", f"${remediated_untagged_cost:,.2f}", delta=f"${remediated_untagged_cost - original_untagged_cost:,.2f}")

    csv_remediated = remediated_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Remediated Dataset",
        data=csv_remediated,
        file_name="cloudmart_remediated.csv",
        mime="text/csv"
    )

    st.markdown("### Governance Improvement Reflection")

    with st.expander("💡 Key Insights and Recommendations"):
        improvement_percentage = ((original_untagged - remediated_untagged) / original_untagged * 100) if original_untagged > 0 else 0
        cost_visibility_improvement = original_untagged_cost - remediated_untagged_cost

        st.write(f"""
        **Impact of Tag Remediation:**

        📊 **Compliance Improvement:** {improvement_percentage:.1f}% reduction in untagged resources

        💰 **Cost Visibility Gain:** ${cost_visibility_improvement:,.2f} in previously hidden costs now attributed

        **Governance Recommendations:**

        1. **Implement Tagging Policies:** Enforce mandatory tags (Department, Project, Environment) at resource creation
        2. **Automated Remediation:** Use AWS Config Rules or Lambda functions to auto-tag resources based on patterns
        3. **Cost Allocation:** Establish clear showback/chargeback models using cost centers
        4. **Regular Audits:** Schedule monthly tagging compliance reviews with department heads
        5. **Training Programs:** Educate teams on the business value of proper resource tagging
        6. **Governance Tools:** Implement AWS Resource Groups and Tag Editor for bulk operations

        **Business Impact:**
        - Improved financial accountability across departments
        - Better resource optimization and rightsizing decisions
        - Enhanced compliance and audit readiness
        - Clearer cloud cost forecasting and budgeting
        """)

st.markdown("---")

st.subheader("📋 Executive Summary")

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_resources = len(df)
    st.metric("Total Resources", total_resources)

with col2:
    untagged_resources = (df['Tagged'] == 'No').sum()
    untagged_percentage = (untagged_resources / total_resources) * 100
    st.metric("Untagged Resources", f"{untagged_percentage:.1f}%")

with col3:
    total_monthly_cost = df['MonthlyCostUSD'].sum()
    st.metric("Total Monthly Cost", f"${total_monthly_cost:,.0f}")

with col4:
    untagged_cost = df[df['Tagged'] == 'No']['MonthlyCostUSD'].sum()
    untagged_cost_percentage = (untagged_cost / total_monthly_cost) * 100
    st.metric("Untagged Cost", f"{untagged_cost_percentage:.1f}%")

st.markdown("---")
st.markdown("**🏷️ CloudMart Resource Tagging Analysis - Cost Governance Dashboard**")