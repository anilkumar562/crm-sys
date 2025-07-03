import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# Database connection details
DB_HOST = "localhost"
DB_NAME = "database"
DB_USER = "anil"
DB_PASS = "9409030562"

# Dropdown options
QUERY_SOURCES = [
    "Mobile", "WhatsApp", "InstaGram", "Gmail", "Facebook"
]

QUERY_TYPE_REASON_SUBREASON = {
    "Return": {
        "Return Arrange": [
            "Quality Issue",
            "Color Issue",
            "Damaged",
            "Wrong Product",
            "Fabric Issue"
        ],
        "Re-Arrange": [
            "Tag Issue",
            "Image Issue",
            "Color Issue",
            "Pickup boy not come",
            "Pickup Delayed"
        ],
        "Pickup Pending": [],
        "Cancel Request": []
    },
    "Exchange": {
        "Size Issue": ["Big Size", "Small Size"],
        "Color Issue": [],
        "Damaged": [],
        "Wrong Product": [],
        "Fabric Issue": [],
        "Cancel Request": [],
        "Re-Arrange": []
    },
    "Refund": {
        "RTO Refund": [],
        "Cancel Refund": [],
        "Missing Product": [],
        "Wrong Delivered Mark": [],
        "Return Product": [],
        "Lost": [],
        "Coupon Code": [],
        "Damaged": []
    },
    "Dispatch": {
        "COD": [
            "Pickup Pending",
            "Missing Product",
            "Wrong Delivered Mark"
        ],
        "Prepaid": [
            "Pickup Pending",
            "Missing Product",
            "Wrong Delivered Mark"
        ]
    },
    "Order Cancel": {
        "COD": [
            "Placed By Mistake",
            "Out of station",
            "Pickup Pending",
            "Out of Stock",
            "Find other Product"
        ],
        "Prepaid": [
            "Placed By Mistake",
            "Out of station",
            "Pickup Pending",
            "Out of Stock",
            "Find other Product"
        ]
    },
    "Delivery Issue": {
        "Wrong Status Marked": [],
        "Wrong product Delivered": []
    },
    "Review Coupon": {}
}

def get_connection():
    return psycopg2.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS
    )

def fetch_tickets():
    with get_connection() as conn:
        df = pd.read_sql("SELECT * FROM tickets ORDER BY id DESC", conn)
    return df

def get_next_case_count(order_number):
    if not order_number:
        return 1
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM tickets WHERE order_number=%s", (order_number,))
            count = cur.fetchone()[0]
            return count + 1

def insert_ticket(data):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tickets (
                    ticket_date, order_number, agent_name, qc_on_off, priority, query_source, query_type,
                    reason, sub_reason, customer_comment, remark, case_count, operational_remark, agent, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, data)
            conn.commit()


def show():

    # Initialize session state
    if 'show_create_ticket' not in st.session_state:
        st.session_state.show_create_ticket = False

    # Show tickets table or create ticket form based on session state
    if not st.session_state.show_create_ticket:
        # Main page with view tickets
        st.subheader("All Tickets")
        
        # Create ticket button
        if st.button("➕ Create New Ticket"):
            st.session_state.show_create_ticket = True
            st.rerun()
        
        # Display tickets
        tickets = fetch_tickets()
        st.dataframe(tickets, hide_index=True, use_container_width=True)

    else:
        # Create ticket page
        st.subheader("🎫 Create New Ticket")
        
        # Back button
        if st.button("⬅️ Back to Tickets"):
            st.session_state.show_create_ticket = False
            st.rerun()
        
        st.markdown("---")
        
        # Auto-set current date and time
        ticket_date = datetime.now()
        
        # Auto-get logged in user name from session state
        logged_in_user = st.session_state.get('user_name', 'Unknown User')
        
        # Auto-populate agent name without showing the field
        agent_name = logged_in_user
        
        # Create ticket form
        order_number = st.text_input("Order Number")
        
        # QC ON/OFF and Priority side by side
        col1, col2 = st.columns(2)
        with col1:
            qc_on_off = st.selectbox("QC ON/OFF", [True, False])
        with col2:
            priority = st.selectbox("Priority", ["Low", "Medium", "High"])
        
        # Query Source and Agent side by side
        col3, col4 = st.columns(2)
        with col3:
            query_source = st.selectbox("Query Source", QUERY_SOURCES)
        with col4:
            # Auto-populate agent field with logged in user
            agent = st.text_input("Agent", value=logged_in_user)
        
        # Dynamic fields for real-time updates
        query_type = st.selectbox("Query Type", list(QUERY_TYPE_REASON_SUBREASON.keys()))
        
        # Get reason options based on selected query type
        reason_options = list(QUERY_TYPE_REASON_SUBREASON.get(query_type, {}).keys())
        if reason_options:
            reason = st.selectbox("Reason", reason_options)
        else:
            reason = st.text_input("Reason")
        
        # Dynamic Sub Reason based on Query Type and Reason
        if reason_options and reason:
            sub_reason_options = QUERY_TYPE_REASON_SUBREASON.get(query_type, {}).get(reason, [])
            if sub_reason_options:
                sub_reason = st.selectbox("Sub Reason", sub_reason_options)
            else:
                sub_reason = st.text_input("Sub Reason (if any)")
        else:
            sub_reason = st.text_input("Sub Reason (if any)")
        
        # Customer Comment and Remark side by side
        col5, col6 = st.columns(2)
        with col5:
            customer_comment = st.text_area("Customer Comment")
        with col6:
            remark = st.text_area("Remark")
        
        # Operational Remark (full width)
        operational_remark = st.text_area("Operational Remark")
        status = "Open"  # Always set to Open for new tickets
        
        st.markdown("---")
        
        # Submit and Cancel buttons
        col1, col2, col3 = st.columns([2, 2, 6])
        with col1:
            if st.button("✅ Submit Ticket", use_container_width=True):
                # Auto-calculate case_count
                case_count = get_next_case_count(order_number) if order_number else 1
                insert_ticket((
                    ticket_date, order_number, agent_name, qc_on_off, priority, query_source, query_type,
                    reason, sub_reason, customer_comment, remark, case_count, operational_remark, agent, status
                ))
                st.success("Ticket created successfully!")
                st.session_state.show_create_ticket = False
                st.rerun()
    
        with col2:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.show_create_ticket = False
                st.rerun()