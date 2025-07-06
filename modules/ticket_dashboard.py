import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import psycopg2
from contextlib import contextmanager
import yaml

# Database connection function
@contextmanager
def get_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="database",
        user="anil",
        password="9409030562"
    )
    try:
        yield conn
    finally:
        conn.close()

# Load dropdown options from YAML
@st.cache_data
def load_dropdown_options():
    try:
        with open('modules/dropdowns.yaml', 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        st.error("dropdowns.yaml file not found!")
        return {}

# Load YAML data
dropdown_data = load_dropdown_options()
AGENTS = dropdown_data.get('agents', [])

# Data fetching functions
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_dashboard_data():
    """Fetch all necessary data for dashboard"""
    with get_connection() as conn:
        # Fetch tickets
        tickets_df = pd.read_sql("""
            SELECT id, ticket_date, order_number, agent_name, qc_on_off, priority, 
                   query_source, query_type, reason, sub_reason, customer_comment, 
                   remark, case_count, operational_remark, agent, status,
                   EXTRACT(HOUR FROM CURRENT_TIMESTAMP - ticket_date::timestamp) as hours_old
            FROM tickets 
            ORDER BY id DESC
        """, conn)
        
        # Fetch ticket logs
        logs_df = pd.read_sql("""
            SELECT ticket_id, log_time, action, by_user 
            FROM ticket_logs 
            ORDER BY log_time DESC
        """, conn)
        
        # Fetch attachments count
        attachments_df = pd.read_sql("""
            SELECT ticket_id, COUNT(*) as attachment_count,
                   SUM(file_size) as total_file_size
            FROM ticket_attachments 
            GROUP BY ticket_id
        """, conn)
        
    return tickets_df, logs_df, attachments_df

def get_ticket_metrics(tickets_df):
    """Calculate key metrics"""
    total_tickets = len(tickets_df)
    open_tickets = len(tickets_df[tickets_df['status'] == 'Open'])
    pending_tickets = len(tickets_df[tickets_df['status'] == 'Pending'])
    closed_tickets = len(tickets_df[tickets_df['status'] == 'Closed'])
    resolved_tickets = len(tickets_df[tickets_df['status'] == 'Resolved'])
    
    # Calculate average resolution time for closed/resolved tickets
    closed_resolved = tickets_df[tickets_df['status'].isin(['Closed', 'Resolved'])]
    avg_resolution_hours = closed_resolved['hours_old'].mean() if not closed_resolved.empty else 0
    
    return {
        'total': total_tickets,
        'open': open_tickets,
        'pending': pending_tickets,
        'closed': closed_tickets,
        'resolved': resolved_tickets,
        'avg_resolution_hours': avg_resolution_hours
    }

def show():
    # st.set_page_config(page_title="Ticket Dashboard", page_icon="📊", layout="wide")
    
    st.title("📊 Ticket Dashboard")
    st.markdown("---")
    
    # Fetch data
    try:
        tickets_df, logs_df, attachments_df = fetch_dashboard_data()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return
    
    if tickets_df.empty:
        st.info("No tickets found in the system.")
        return
    
    # Get metrics
    metrics = get_ticket_metrics(tickets_df)
    
    # Date filter
    col1, col2, col3 = st.columns([2, 2, 6])
    with col1:
        start_date = st.date_input("From Date", 
                                  value=datetime.now().date() - timedelta(days=30),
                                  max_value=datetime.now().date())
    with col2:
        end_date = st.date_input("To Date", 
                                value=datetime.now().date(),
                                max_value=datetime.now().date())
    
    # Filter tickets by date
    filtered_tickets = tickets_df[
        (pd.to_datetime(tickets_df['ticket_date']).dt.date >= start_date) &
        (pd.to_datetime(tickets_df['ticket_date']).dt.date <= end_date)
    ]
    
    if filtered_tickets.empty:
        st.warning("No tickets found in the selected date range.")
        return
    
    # Key Metrics Row
    st.subheader("📈 Key Metrics")
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("Total Tickets", metrics['total'])
    
    with col2:
        st.metric("Open", metrics['open'], 
                 delta=f"{metrics['open']} active" if metrics['open'] > 0 else None)
    
    with col3:
        st.metric("Pending", metrics['pending'],
                 delta=f"{metrics['pending']} waiting" if metrics['pending'] > 0 else None)
    
    with col4:
        st.metric("Closed", metrics['closed'])
    
    with col5:
        st.metric("Resolved", metrics['resolved'])
    
    with col6:
        avg_hours = round(metrics['avg_resolution_hours'], 1)
        st.metric("Avg Resolution", f"{avg_hours}h")
    
    st.markdown("---")
    
    # Charts Row 1
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 Ticket Status Distribution")
        status_counts = filtered_tickets['status'].value_counts()
        
        # Create pie chart
        fig_pie = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            title="Tickets by Status",
            color_discrete_map={
                'Open': '#ff6b6b',
                'Pending': '#ffa726',
                'Closed': '#66bb6a',
                'Resolved': '#42a5f5'
            }
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        st.subheader("📊 Priority Distribution")
        priority_counts = filtered_tickets['priority'].value_counts()
        
        fig_priority = px.bar(
            x=priority_counts.index,
            y=priority_counts.values,
            title="Tickets by Priority",
            color=priority_counts.index,
            color_discrete_map={
                'High': '#ff4444',
                'Medium': '#ffaa00',
                'Low': '#00aa00'
            }
        )
        fig_priority.update_layout(showlegend=False)
        st.plotly_chart(fig_priority, use_container_width=True)
    
    # Charts Row 2
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("👥 Tickets by Agent")
        agent_counts = filtered_tickets['agent'].value_counts().head(10)
        
        fig_agent = px.bar(
            x=agent_counts.values,
            y=agent_counts.index,
            orientation='h',
            title="Top 10 Agents by Ticket Count",
            color=agent_counts.values,
            color_continuous_scale='Blues'
        )
        fig_agent.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_agent, use_container_width=True)
    
    with col2:
        st.subheader("📱 Query Sources")
        source_counts = filtered_tickets['query_source'].value_counts()
        
        fig_source = px.bar(
            x=source_counts.index,
            y=source_counts.values,
            title="Tickets by Query Source",
            color=source_counts.values,
            color_continuous_scale='Greens'
        )
        fig_source.update_layout(showlegend=False, xaxis_tickangle=45)
        st.plotly_chart(fig_source, use_container_width=True)
    
    # Time Series Chart
    st.subheader("📅 Ticket Creation Trend")
    
    # Group by date
    daily_tickets = filtered_tickets.groupby('ticket_date').size().reset_index(name='count')
    daily_tickets['ticket_date'] = pd.to_datetime(daily_tickets['ticket_date'])
    
    fig_timeline = px.line(
        daily_tickets,
        x='ticket_date',
        y='count',
        title="Daily Ticket Creation",
        markers=True
    )
    fig_timeline.update_layout(
        xaxis_title="Date",
        yaxis_title="Number of Tickets"
    )
    st.plotly_chart(fig_timeline, use_container_width=True)
    
    # Query Type Analysis
    st.subheader("🔍 Query Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Top Query Types**")
        query_type_counts = filtered_tickets['query_type'].value_counts().head(10)
        for idx, (query_type, count) in enumerate(query_type_counts.items(), 1):
            st.write(f"{idx}. {query_type}: **{count}** tickets")
    
    with col2:
        st.write("**Top Reasons**")
        reason_counts = filtered_tickets['reason'].value_counts().head(10)
        for idx, (reason, count) in enumerate(reason_counts.items(), 1):
            st.write(f"{idx}. {reason}: **{count}** tickets")
    
    # Recent Activity
    st.subheader("🕒 Recent Activity")
    
    if not logs_df.empty:
        recent_logs = logs_df.head(10)
        
        for _, log in recent_logs.iterrows():
            time_str = log['log_time'].strftime('%Y-%m-%d %H:%M:%S')
            st.markdown(
                f"""
                <div style="border:1px solid #eee; border-radius:6px; padding:8px; margin-bottom:8px;">
                    <b>Ticket #{log['ticket_id']}</b> - {log['action']} 
                    <br><small style="color:#666;">{time_str} by {log['by_user']}</small>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.info("No recent activity found.")
    
    # Agent Performance Table
    st.subheader("👤 Agent Performance")
    
    if not filtered_tickets.empty:
        agent_performance = filtered_tickets.groupby('agent').agg({
            'id': 'count',
            'status': lambda x: (x == 'Closed').sum() + (x == 'Resolved').sum(),
            'priority': lambda x: (x == 'High').sum(),
            'hours_old': 'mean'
        }).round(1)
        
        agent_performance.columns = ['Total Tickets', 'Resolved/Closed', 'High Priority', 'Avg Hours Open']
        agent_performance['Resolution Rate %'] = (
            (agent_performance['Resolved/Closed'] / agent_performance['Total Tickets'] * 100)
            .round(1)
        )
        
        # Sort by total tickets descending
        agent_performance = agent_performance.sort_values('Total Tickets', ascending=False)
        
        st.dataframe(agent_performance, use_container_width=True)
    
    # File Attachments Summary
    if not attachments_df.empty:
        st.subheader("📎 File Attachments Summary")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_attachments = attachments_df['attachment_count'].sum()
            st.metric("Total Attachments", total_attachments)
        
        with col2:
            tickets_with_files = len(attachments_df)
            st.metric("Tickets with Files", tickets_with_files)
        
        with col3:
            total_size_mb = (attachments_df['total_file_size'].sum() / (1024 * 1024))
            st.metric("Total File Size", f"{total_size_mb:.1f} MB")
    
    # Auto-refresh button
    st.markdown("---")
    col1, col2, col3 = st.columns([6, 2, 2])
    with col2:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    with col3:
        st.write(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    show()
