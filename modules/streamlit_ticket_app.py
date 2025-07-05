import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
import os

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


def fetch_ticket_by_id(ticket_id):
    with get_connection() as conn:
        df = pd.read_sql("SELECT * FROM tickets WHERE id=%s", conn, params=(ticket_id,))
    return df.iloc[0] if not df.empty else None

def update_ticket_status_remark(ticket_id, status, operational_remark):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tickets SET status=%s, operational_remark=%s WHERE id=%s",
                (status, operational_remark, ticket_id)
            )
            conn.commit()

def get_open_ticket_by_order(order_number):
    with get_connection() as conn:
        df = pd.read_sql(
            "SELECT * FROM tickets WHERE order_number=%s AND status='Open' ORDER BY id DESC",
            conn,
            params=(order_number,)
        )
    return df.iloc[0] if not df.empty else None

def insert_ticket_log(ticket_id, order_number, action, comment, by_user):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ticket_logs (ticket_id, order_number, log_time, action, comment, by_user)
                VALUES (%s, %s, NOW(), %s, %s, %s)
                """,
                (ticket_id, order_number, action, comment, by_user)
            )
            conn.commit()

def save_uploaded_file(uploaded_file, ticket_id):
    """Save uploaded file to local filesystem and return the file path"""
    if uploaded_file is not None:
        # Create uploads directory if it doesn't exist
        upload_dir = "uploads"
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        # Generate unique filename with ticket ID and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = uploaded_file.name.split('.')[-1]
        filename = f"ticket_{ticket_id}_{timestamp}.{file_extension}"
        file_path = os.path.join(upload_dir, filename)
        
        # Save the file
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return file_path
    return None

def save_file_to_database(uploaded_file, ticket_id, uploaded_by):
    """Save uploaded file to database and return the attachment ID"""
    if uploaded_file is not None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Get file info
                file_data = uploaded_file.getbuffer()
                file_name = uploaded_file.name
                file_type = uploaded_file.type if uploaded_file.type else file_name.split('.')[-1]
                file_size = len(file_data)
                
                # Insert into database
                cur.execute("""
                    INSERT INTO ticket_attachments 
                    (ticket_id, file_name, file_type, file_size, uploaded_at, uploaded_by, file_data)
                    VALUES (%s, %s, %s, %s, NOW(), %s, %s)
                    RETURNING id
                """, (ticket_id, file_name, file_type, file_size, uploaded_by, file_data))
                
                attachment_id = cur.fetchone()[0]
                conn.commit()
                return attachment_id
    return None

def get_ticket_attachments(ticket_id):
    """Get all attachments for a ticket (without file data)"""
    with get_connection() as conn:
        df = pd.read_sql("""
            SELECT id, file_name, file_type, file_size, uploaded_at, uploaded_by 
            FROM ticket_attachments 
            WHERE ticket_id=%s 
            ORDER BY uploaded_at DESC
        """, conn, params=(ticket_id,))
    return df

def download_attachment(attachment_id):
    """Download attachment file data from database"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT file_name, file_type, file_data 
                FROM ticket_attachments 
                WHERE id=%s
            """, (attachment_id,))
            result = cur.fetchone()
            if result:
                file_name, file_type, file_data = result
                # Convert memoryview to bytes
                if isinstance(file_data, memoryview):
                    file_data = file_data.tobytes()
                return file_name, file_type, file_data
    return None, None, None

def show():
    if 'show_create_ticket' not in st.session_state:
        st.session_state.show_create_ticket = False
    if 'view_ticket_id' not in st.session_state:
        st.session_state.view_ticket_id = None

    if st.session_state.view_ticket_id:
        # ----------- VIEW/EDIT TICKET PAGE -----------
        ticket = fetch_ticket_by_id(st.session_state.view_ticket_id)
        if ticket is None:
            st.error("Ticket not found.")
            st.session_state.view_ticket_id = None
            st.rerun()
        st.subheader(f"🎫 Ticket #{ticket['id']} Details")
        st.markdown("---")

        # Ticket Date (disabled) - moved above Order Number
        st.text_input("Ticket Date", value=str(ticket['ticket_date']), disabled=True)

        # Order Number (disabled)
        st.text_input("Order Number", value=ticket['order_number'], disabled=True)

        # QC ON/OFF and Priority side by side (disabled)
        col1, col2 = st.columns(2)
        with col1:
            st.selectbox("QC ON/OFF", [True, False], index=0 if ticket['qc_on_off'] else 1, disabled=True)
        with col2:
            st.selectbox("Priority", ["Low", "Medium", "High"], index=["Low", "Medium", "High"].index(ticket['priority']), disabled=True)

        # Query Source and Agent side by side (disabled)
        col3, col4 = st.columns(2)
        with col3:
            st.selectbox("Query Source", QUERY_SOURCES, index=QUERY_SOURCES.index(ticket['query_source']), disabled=True)
        with col4:
            st.text_input("Agent", value=ticket['agent'], disabled=True)

        # Query Type, Reason, Sub Reason (disabled)
        st.selectbox("Query Type", list(QUERY_TYPE_REASON_SUBREASON.keys()), index=list(QUERY_TYPE_REASON_SUBREASON.keys()).index(ticket['query_type']), disabled=True)
        reason_options = list(QUERY_TYPE_REASON_SUBREASON.get(ticket['query_type'], {}).keys())
        if reason_options:
            st.selectbox("Reason", reason_options, index=reason_options.index(ticket['reason']), disabled=True)
        else:
            st.text_input("Reason", value=ticket['reason'], disabled=True)
        if reason_options and ticket['reason']:
            sub_reason_options = QUERY_TYPE_REASON_SUBREASON.get(ticket['query_type'], {}).get(ticket['reason'], [])
            if sub_reason_options:
                st.selectbox("Sub Reason", sub_reason_options, index=sub_reason_options.index(ticket['sub_reason']) if ticket['sub_reason'] in sub_reason_options else 0, disabled=True)
            else:
                st.text_input("Sub Reason (if any)", value=ticket['sub_reason'], disabled=True)
        else:
            st.text_input("Sub Reason (if any)", value=ticket['sub_reason'], disabled=True)

        # Customer Comment and Remark side by side (disabled)
        col5, col6 = st.columns(2)
        with col5:
            st.text_area("Customer Comment", value=ticket['customer_comment'], disabled=True)
        with col6:
            st.text_area("Remark", value=ticket['remark'], disabled=True)

        # Operational Remark (editable)
        operational_remark = st.text_area("Operational Remark", value=ticket['operational_remark'] or "")
        
        # File attachment (same width as Operational Remark)
        uploaded_file = st.file_uploader("📎 Attach File", type=['pdf', 'jpg', 'jpeg', 'png'], key="file_uploader")

        # Status (editable)
        status = st.selectbox(
            "Status",
            ["Open", "Closed", "Pending", "Resolved"],
            index=["Open", "Closed", "Pending", "Resolved"].index(ticket['status']) if ticket['status'] in ["Open", "Closed", "Pending", "Resolved"] else 0
        )

        st.markdown("---")
        col1, col2, col3 = st.columns([2, 2, 6])
        with col1:
            if st.button("💾 Update Ticket", use_container_width=True):
                # Get logged in user
                logged_in_user = st.session_state.get('user_name', 'Unknown User')
                
                # Check if status or operational_remark changed
                status_changed = ticket['status'] != status
                remark_changed = (ticket['operational_remark'] or '') != operational_remark
                
                # Update the ticket
                update_ticket_status_remark(int(ticket['id']), status, operational_remark)
                
                # Handle file upload if a file is attached
                if uploaded_file is not None:
                    # Save the file to database and get the attachment ID
                    attachment_id = save_file_to_database(uploaded_file, int(ticket['id']), logged_in_user)
                    # Log the file attachment
                    insert_ticket_log(
                        ticket_id=int(ticket['id']),
                        order_number=ticket['order_number'],
                        action="File attached during ticket update",
                        comment=f"File attached: {uploaded_file.name}, Attachment ID: {attachment_id}",
                        by_user=logged_in_user
                    )
                
                # Log the changes
                if status_changed:
                    insert_ticket_log(
                        ticket_id=int(ticket['id']),
                        order_number=ticket['order_number'],
                        action=f"Status changed from {ticket['status']} to {status}",
                        comment=f"Status updated by {logged_in_user}",
                        by_user=logged_in_user
                    )
                
                if remark_changed:
                    insert_ticket_log(
                        ticket_id=int(ticket['id']),
                        order_number=ticket['order_number'],
                        action="Operational Remark updated",
                        comment=operational_remark,
                        by_user=logged_in_user
                    )
                
                st.success("Ticket updated successfully!")
                st.session_state.view_ticket_id = None
                st.rerun()
        with col2:
            if st.button("⬅️ Back", use_container_width=True):
                st.session_state.view_ticket_id = None
                st.rerun()
        st.markdown("---")
        
        # Add comment section (moved above logs)
        st.subheader("Add Comment")
        col_comment, col_send = st.columns([6, 1])
        with col_comment:
            new_comment = st.text_input("Comment", placeholder="Add a comment...")
        with col_send:
            st.markdown("<br>", unsafe_allow_html=True)  # Add spacing to align with text input
            if st.button("Send", use_container_width=True):
                if new_comment.strip() or uploaded_file is not None:
                    logged_in_user = st.session_state.get('user_name', 'Unknown User')
                    
                    # Prepare comment with file info if file is uploaded
                    comment_text = new_comment
                    if uploaded_file is not None:
                        # Save the file to database and get the attachment ID
                        attachment_id = save_file_to_database(uploaded_file, int(ticket['id']), logged_in_user)
                        comment_text += f" [File attached: {uploaded_file.name}, Attachment ID: {attachment_id}]"
                    
                    insert_ticket_log(
                        ticket_id=int(ticket['id']),
                        order_number=ticket['order_number'],
                        action="Comment added" if not uploaded_file else "Comment with attachment added",
                        comment=comment_text,
                        by_user=logged_in_user
                    )
                    # st.success("Comment added successfully!")
                    st.rerun()
                else:
                    st.warning("Please enter a comment or attach a file.")
        
        st.markdown("---")
        
        # Show attachments section
        st.subheader("📎 Attachments")
        attachments = get_ticket_attachments(int(ticket['id']))
        if not attachments.empty:
            for idx, attachment in attachments.iterrows():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                with col1:
                    st.write(f"📄 {attachment['file_name']}")
                with col2:
                    st.write(f"{attachment['file_size']} bytes")
                with col3:
                    st.write(attachment['uploaded_at'].strftime('%Y-%m-%d %H:%M'))
                with col4:
                    if st.button("Download", key=f"download_{attachment['id']}"):
                        file_name, file_type, file_data = download_attachment(attachment['id'])
                        if file_data:
                            st.download_button(
                                label=f"💾 {file_name}",
                                data=file_data,
                                file_name=file_name,
                                mime=file_type,
                                key=f"dl_{attachment['id']}"
                            )
        else:
            st.info("No attachments for this ticket.")
        
        st.markdown("---")
        logs = None
        with get_connection() as conn:
            logs = pd.read_sql(
                "SELECT log_time, action, comment, by_user FROM ticket_logs WHERE ticket_id=%s ORDER BY log_time DESC",
                conn,
                params=(int(ticket['id']),)
            )
        if logs is not None and not logs.empty:
            for idx, log in logs.iterrows():
                st.markdown(
                    f"""
                    <div style="border:1px solid #eee; border-radius:6px; padding:8px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:flex-start;">
                        <div>
                            <b>{log['log_time'].strftime('%Y-%m-%d %H:%M:%S')}</b> | <b>{log['action']}</b><br>
                            <span style="color:#555;">{log['comment'] if log['comment'] else ''}</span>
                        </div>
                        <div style="text-align:right; font-weight:bold; color:#666;">
                            {log['by_user']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("No logs for this ticket yet.")

        st.markdown("---")
        return

    # ----------- MAIN/CREATE TICKET PAGE -----------
    if not st.session_state.show_create_ticket:
        st.subheader("All Tickets")
        
        # Create button and search in the same row
        col_create, col_search = st.columns([2, 3])
        with col_create:
            if st.button("➕ Create New Ticket"):
                st.session_state.show_create_ticket = True
                st.rerun()
        with col_search:
            search_term = st.text_input("", placeholder="🔍 Search by Ticket No, Order Number", key="ticket_search")
        
        tickets = fetch_tickets()
        
        # Filter tickets based on search term
        if not tickets.empty and search_term:
            search_term = search_term.lower()
            tickets = tickets[
                tickets['id'].astype(str).str.lower().str.contains(search_term, na=False) |
                tickets['order_number'].astype(str).str.lower().str.contains(search_term, na=False)
        ]
        
        if not tickets.empty:
            tickets = tickets.copy()
            tickets['View'] = tickets['id'].apply(lambda tid: f"view_{tid}")
            # Add top border
            st.markdown('<hr style="border:2px solid #bbb; margin-top:0; margin-bottom:10px;">', unsafe_allow_html=True)
            # Header row
            header_cols = st.columns([1, 2, 2, 2, 2, 2, 1])
            header_cols[0].markdown("**Ticket No**")
            header_cols[1].markdown("**Order Number**")
            header_cols[2].markdown("**Query Type**")
            header_cols[3].markdown("**Reason**")
            header_cols[4].markdown("**Status**")
            header_cols[5].markdown("**Ticket Date**")
            header_cols[6].markdown("**Action**")
            # Ticket rows with 1px border between
            for idx, row in tickets.iterrows():
                st.markdown(
                    '<div style="border-top:1px solid #ddd; margin-top:0; margin-bottom:0;"></div>',
                    unsafe_allow_html=True
                )
                cols = st.columns([1, 2, 2, 2, 2, 2, 1])
                cols[0].write(row['id'])  # Ticket No
                cols[1].write(row['order_number'])
                cols[2].write(row['query_type'])
                cols[3].write(row['reason'])
                cols[4].write(row['status'])
                cols[5].write(str(row['ticket_date']))
                if cols[6].button("View", key=f"viewbtn_{row['id']}"):
                    st.session_state.view_ticket_id = row['id']
                    st.rerun()
            # Add bottom border
            st.markdown('<hr style="border:2px solid #bbb; margin-top:10px; margin-bottom:0;">', unsafe_allow_html=True)
        else:
            st.info("No tickets found.")
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
        
        # Check for existing open ticket for this order number
        open_ticket = None
        if order_number:
            open_ticket = get_open_ticket_by_order(order_number)
            # Also check for Pending status
            if open_ticket is None:
                with get_connection() as conn:
                    df_pending = pd.read_sql(
                        "SELECT * FROM tickets WHERE order_number=%s AND status='Pending' ORDER BY id DESC",
                        conn,
                        params=(order_number,)
                    )
                if not df_pending.empty:
                    open_ticket = df_pending.iloc[0]
            if open_ticket is not None:
                st.warning(
                    f"Ticket already open for this Order Number! (Ticket No: {open_ticket['id']}, Status: {open_ticket['status']})"
                )
                if st.button("View Open Ticket", key="view_open_ticket"):
                    st.session_state.show_create_ticket = False
                    st.session_state.view_ticket_id = int(open_ticket['id'])
                    st.rerun()

        # Only show the rest of the form if no open or pending ticket exists for this order number
        if open_ticket is None:
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
            
            # File attachment for new ticket
            uploaded_file = st.file_uploader("📎 Attach File", type=['pdf', 'jpg', 'jpeg', 'png'], key="new_ticket_file_uploader")
            
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
                    
                    # Get the last inserted ticket id
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("SELECT id FROM tickets WHERE order_number=%s ORDER BY id DESC LIMIT 1", (order_number,))
                            new_ticket_id = cur.fetchone()[0]

                    # Handle file upload if a file is attached
                    if uploaded_file is not None:
                        # Save the file to database and get the attachment ID
                        attachment_id = save_file_to_database(uploaded_file, new_ticket_id, logged_in_user)
                        # Log the file attachment
                        insert_ticket_log(
                            ticket_id=new_ticket_id,
                            order_number=order_number,
                            action="File attached during ticket creation",
                            comment=f"File attached: {uploaded_file.name}, Attachment ID: {attachment_id}",
                            by_user=logged_in_user
                        )

                    insert_ticket_log(
                        ticket_id=new_ticket_id,
                        order_number=order_number,
                        action="Created",
                        comment="Ticket created",
                        by_user=logged_in_user
                    )
                    
                    st.success("Ticket created successfully!")
                    st.session_state.show_create_ticket = False
                    st.rerun()
        
            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.show_create_ticket = False
                    st.rerun()