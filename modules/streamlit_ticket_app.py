import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
import os
import yaml

# Database connection details
DB_HOST = "localhost"
DB_NAME = "database"
DB_USER = "anil"
DB_PASS = "9409030562"

# Load dropdown options from YAML file
def load_dropdown_config():
    """Load dropdown configuration from YAML file"""
    try:
        yaml_path = os.path.join(os.path.dirname(__file__), 'dropdowns.yaml')
        with open(yaml_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
            return config
    except FileNotFoundError:
        st.error("dropdowns.yaml file not found. Please ensure it exists in the modules folder.")
        return {"sources": [], "query_type_reason_subreason": {}}
    except yaml.YAMLError as e:
        st.error(f"Error parsing dropdowns.yaml: {e}")
        return {"sources": [], "query_type_reason_subreason": {}}

# Load configuration
dropdown_config = load_dropdown_config()
QUERY_SOURCES = dropdown_config.get('sources', [])
QUERY_TYPE_REASON_SUBREASON = dropdown_config.get('query_type_reason_subreason', {})
AGENTS = dropdown_config.get('agents', [])

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

def update_ticket_creator_fields(ticket_id, order_number, qc_on_off, priority, query_source, agent, query_type, reason, sub_reason, customer_comment, remark):
    """Update ticket fields that can be edited by the ticket creator"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE tickets SET 
                   order_number=%s, qc_on_off=%s, priority=%s, query_source=%s, 
                   agent=%s, query_type=%s, reason=%s, sub_reason=%s, 
                   customer_comment=%s, remark=%s 
                   WHERE id=%s""",
                (order_number, qc_on_off, priority, query_source, agent, 
                 query_type, reason, sub_reason, customer_comment, remark, ticket_id)
            )
            conn.commit()

def safe_string_compare(old_val, new_val):
    """Safely compare two values that might be None, handling empty strings and None as equivalent"""
    old_str = str(old_val) if old_val is not None else ''
    new_str = str(new_val) if new_val is not None else ''
    return old_str != new_str

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
    # Global CSS to hide file uploader help text but keep label
    st.markdown("""
    <style>
    .stFileUploader > label + div > div > div > div:nth-child(2) {
        display: none !important;
    }
    .stFileUploader small {
        display: none !important;
    }
    .stFileUploader > label + div small {
        display: none !important;
    }
    .stFileUploader > label + div p {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
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
        st.subheader(f"🎫 Ticket #{ticket['id']} Details - {ticket['ticket_date'].strftime('%Y-%m-%d')}")
        st.markdown("---")

        # Check if logged in user is the ticket creator
        logged_in_user = st.session_state.get('user_name', 'Unknown User')
        is_ticket_creator = (logged_in_user == ticket['agent_name'])
        
        # Order Number (editable by ticket creator)
        order_number = st.text_input("Order Number", 
                                   value=ticket['order_number'], 
                                   disabled=not is_ticket_creator,
                                   help="Only the ticket creator can edit this field" if not is_ticket_creator else None)

        # QC ON/OFF and Priority side by side (editable by ticket creator)
        col1, col2 = st.columns(2)
        with col1:
            qc_on_off = st.selectbox("QC ON/OFF", 
                                   [True, False], 
                                   index=0 if ticket['qc_on_off'] else 1, 
                                   disabled=not is_ticket_creator,
                                   help="Only the ticket creator can edit this field" if not is_ticket_creator else None)
        with col2:
            priority = st.selectbox("Priority", 
                                  ["Low", "Medium", "High"], 
                                  index=["Low", "Medium", "High"].index(ticket['priority']), 
                                  disabled=not is_ticket_creator,
                                  help="Only the ticket creator can edit this field" if not is_ticket_creator else None)

        # Query Source and Agent side by side (editable by ticket creator)
        col3, col4 = st.columns(2)
        with col3:
            query_source = st.selectbox("Query Source", 
                                      QUERY_SOURCES, 
                                      index=QUERY_SOURCES.index(ticket['query_source']), 
                                      disabled=not is_ticket_creator,
                                      help="Only the ticket creator can edit this field" if not is_ticket_creator else None)
        with col4:
            agent_index = AGENTS.index(ticket['agent']) if ticket['agent'] in AGENTS else 0
            agent = st.selectbox("Agent", 
                               AGENTS, 
                               index=agent_index, 
                               disabled=not is_ticket_creator,
                               help="Only the ticket creator can edit this field" if not is_ticket_creator else None)

        # Query Type, Reason, Sub Reason (editable by ticket creator)
        query_type = st.selectbox("Query Type", 
                                list(QUERY_TYPE_REASON_SUBREASON.keys()), 
                                index=list(QUERY_TYPE_REASON_SUBREASON.keys()).index(ticket['query_type']), 
                                disabled=not is_ticket_creator,
                                help="Only the ticket creator can edit this field" if not is_ticket_creator else None)
        
        # Get reason options based on selected query type
        reason_options = list(QUERY_TYPE_REASON_SUBREASON.get(query_type, {}).keys())
        if reason_options:
            reason_index = reason_options.index(ticket['reason']) if ticket['reason'] in reason_options else 0
            reason = st.selectbox("Reason", 
                                reason_options, 
                                index=reason_index, 
                                disabled=not is_ticket_creator,
                                help="Only the ticket creator can edit this field" if not is_ticket_creator else None)
        else:
            reason = st.text_input("Reason", 
                                 value=ticket['reason'], 
                                 disabled=not is_ticket_creator,
                                 help="Only the ticket creator can edit this field" if not is_ticket_creator else None)
        
        # Dynamic Sub Reason based on Query Type and Reason
        if reason_options and reason:
            sub_reason_options = QUERY_TYPE_REASON_SUBREASON.get(query_type, {}).get(reason, [])
            if sub_reason_options:
                sub_reason_index = sub_reason_options.index(ticket['sub_reason']) if ticket['sub_reason'] in sub_reason_options else 0
                sub_reason = st.selectbox("Sub Reason", 
                                        sub_reason_options, 
                                        index=sub_reason_index, 
                                        disabled=not is_ticket_creator,
                                        help="Only the ticket creator can edit this field" if not is_ticket_creator else None)
            else:
                sub_reason = st.text_input("Sub Reason (if any)", 
                                         value=ticket['sub_reason'], 
                                         disabled=not is_ticket_creator,
                                         help="Only the ticket creator can edit this field" if not is_ticket_creator else None)
        else:
            sub_reason = st.text_input("Sub Reason (if any)", 
                                     value=ticket['sub_reason'], 
                                     disabled=not is_ticket_creator,
                                     help="Only the ticket creator can edit this field" if not is_ticket_creator else None)

        # Customer Comment and Remark side by side (editable by ticket creator)
        col5, col6 = st.columns(2)
        with col5:
            customer_comment = st.text_area("Customer Comment", 
                                          value=ticket['customer_comment'], 
                                          disabled=not is_ticket_creator, 
                                          height=70,
                                          help="Only the ticket creator can edit this field" if not is_ticket_creator else None)
        with col6:
            remark = st.text_area("Remark", 
                                value=ticket['remark'], 
                                disabled=not is_ticket_creator, 
                                height=70,
                                help="Only the ticket creator can edit this field" if not is_ticket_creator else None)

        # Operational Remark and File attachment side by side
        col7, col8 = st.columns(2)
        with col7:
            # Check if logged in user is the ticket agent
            logged_in_user = st.session_state.get('user_name', 'Unknown User')
            is_ticket_agent = (logged_in_user == ticket['agent'])
            
            operational_remark = st.text_area("Operational Remark", 
                                            value=ticket['operational_remark'] or "", 
                                            height=70,
                                            disabled=not is_ticket_agent,
                                            help="Only the assigned agent can edit operational remarks" if not is_ticket_agent else None)
        with col8:
            # File upload accessible to both agent and ticket creator
            can_upload = is_ticket_agent or is_ticket_creator
            uploaded_file = st.file_uploader("📎 Attach File", 
                                            type=['pdf', 'jpg', 'jpeg', 'png', 'mp4', 'mkv', 'mp3'], 
                                            key="file_uploader",
                                            disabled=not can_upload,
                                            help="Only the assigned agent or ticket creator can attach files" if not can_upload else None)

        # Status (editable only by ticket agent)
        status = st.selectbox(
            "Status",
            ["Open", "Closed", "Pending", "Resolved"],
            index=["Open", "Closed", "Pending", "Resolved"].index(ticket['status']) if ticket['status'] in ["Open", "Closed", "Pending", "Resolved"] else 0,
            disabled=not is_ticket_agent,
            help="Only the assigned agent can change the status" if not is_ticket_agent else None
        )

        st.markdown("---")
        col1, col2, col3 = st.columns([2, 2, 6])
        with col1:
            # Allow both agent and ticket creator to update their respective fields
            can_update = is_ticket_agent or is_ticket_creator
            if st.button("💾 Update Ticket", use_container_width=True, disabled=not can_update):
                if is_ticket_agent:
                    # Agent can update status and operational remark
                    changes_made = False
                    
                    # Check if status or operational_remark changed
                    status_changed = safe_string_compare(ticket['status'], status)
                    remark_changed = safe_string_compare(ticket['operational_remark'], operational_remark)
                    
                    # Update the ticket if there are changes
                    if status_changed or remark_changed:
                        update_ticket_status_remark(int(ticket['id']), status, operational_remark)
                        changes_made = True
                    
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
                        changes_made = True
                    
                    # Log the specific changes
                    if status_changed:
                        insert_ticket_log(
                            ticket_id=int(ticket['id']),
                            order_number=ticket['order_number'],
                            action="Status updated by agent",
                            comment=f"Status: '{ticket['status']}' → '{status}'",
                            by_user=logged_in_user
                        )
                    
                    if remark_changed:
                        old_remark = ticket['operational_remark'] or '(empty)'
                        new_remark = operational_remark or '(empty)'
                        insert_ticket_log(
                            ticket_id=int(ticket['id']),
                            order_number=ticket['order_number'],
                            action="Operational Remark updated by agent",
                            comment=f"Operational Remark: '{old_remark}' → '{new_remark}'",
                            by_user=logged_in_user
                        )
                    
                    if changes_made:
                        st.success("Ticket updated successfully!")
                        st.session_state.view_ticket_id = None
                        st.rerun()
                    else:
                        st.info("No changes detected.")
                    
                elif is_ticket_creator:
                    # Ticket creator can update other fields
                    changes_made = False
                    field_changes = []
                    
                    # Check for field changes and log them
                    if safe_string_compare(ticket['order_number'], order_number):
                        field_changes.append(f"Order Number: '{ticket['order_number'] or '(empty)'}' → '{order_number or '(empty)'}'")
                    
                    if ticket['qc_on_off'] != qc_on_off:
                        field_changes.append(f"QC ON/OFF: '{ticket['qc_on_off']}' → '{qc_on_off}'")
                    
                    if safe_string_compare(ticket['priority'], priority):
                        field_changes.append(f"Priority: '{ticket['priority'] or '(empty)'}' → '{priority or '(empty)'}'")
                    
                    if safe_string_compare(ticket['query_source'], query_source):
                        field_changes.append(f"Query Source: '{ticket['query_source'] or '(empty)'}' → '{query_source or '(empty)'}'")
                    
                    if safe_string_compare(ticket['agent'], agent):
                        field_changes.append(f"Agent: '{ticket['agent'] or '(empty)'}' → '{agent or '(empty)'}'")
                    
                    if safe_string_compare(ticket['query_type'], query_type):
                        field_changes.append(f"Query Type: '{ticket['query_type'] or '(empty)'}' → '{query_type or '(empty)'}'")
                    
                    if safe_string_compare(ticket['reason'], reason):
                        field_changes.append(f"Reason: '{ticket['reason'] or '(empty)'}' → '{reason or '(empty)'}'")
                    
                    if safe_string_compare(ticket['sub_reason'], sub_reason):
                        field_changes.append(f"Sub Reason: '{ticket['sub_reason'] or '(empty)'}' → '{sub_reason or '(empty)'}'")
                    
                    if safe_string_compare(ticket['customer_comment'], customer_comment):
                        field_changes.append(f"Customer Comment: '{ticket['customer_comment'] or '(empty)'}' → '{customer_comment or '(empty)'}'")
                    
                    if safe_string_compare(ticket['remark'], remark):
                        field_changes.append(f"Remark: '{ticket['remark'] or '(empty)'}' → '{remark or '(empty)'}'")
                    
                    # Update the ticket with creator editable fields if there are changes
                    if field_changes:
                        update_ticket_creator_fields(
                            int(ticket['id']), 
                            order_number, 
                            qc_on_off, 
                            priority, 
                            query_source, 
                            agent, 
                            query_type, 
                            reason, 
                            sub_reason, 
                            customer_comment, 
                            remark
                        )
                        changes_made = True
                        
                        # Log each field change
                        for change in field_changes:
                            insert_ticket_log(
                                ticket_id=int(ticket['id']),
                                order_number=order_number,
                                action="Field updated by creator",
                                comment=change,
                                by_user=logged_in_user
                            )
                    
                    # Handle file upload if a file is attached
                    if uploaded_file is not None:
                        # Save the file to database and get the attachment ID
                        attachment_id = save_file_to_database(uploaded_file, int(ticket['id']), logged_in_user)
                        # Log the file attachment
                        insert_ticket_log(
                            ticket_id=int(ticket['id']),
                            order_number=order_number,
                            action="File attached during ticket update",
                            comment=f"File attached: {uploaded_file.name}, Attachment ID: {attachment_id}",
                            by_user=logged_in_user
                        )
                        changes_made = True
                    
                    # Show success message if any changes were made
                    if changes_made:
                        st.success("Ticket updated successfully!")
                        st.session_state.view_ticket_id = None
                        st.rerun()
                    else:
                        st.info("No changes detected.")
                else:
                    st.error("You don't have permission to update this ticket.")
        with col2:
            if st.button("⬅️ Back", use_container_width=True):
                st.session_state.view_ticket_id = None
                st.rerun()
        st.markdown("---")
        
        # Add comment section (moved above logs)
        st.subheader("Add Comment")
        
        # Initialize comment clear count if not exists
        if f'comment_clear_count_{ticket["id"]}' not in st.session_state:
            st.session_state[f'comment_clear_count_{ticket["id"]}'] = 0
        
        col_comment, col_send = st.columns([6, 1])
        with col_comment:
            # Create a simpler key to avoid string formatting issues
            clear_count = st.session_state[f'comment_clear_count_{ticket["id"]}']
            comment_key = f"comment_text_{ticket['id']}_{clear_count}"
            new_comment = st.text_input("Comment", 
                                      placeholder="Add a comment...",
                                      key=comment_key)
        with col_send:
            st.markdown("<br>", unsafe_allow_html=True)  # Add spacing to align with text input
            if st.button("Send", use_container_width=True):
                if new_comment.strip() or (uploaded_file is not None and (is_ticket_agent or is_ticket_creator)):
                    logged_in_user = st.session_state.get('user_name', 'Unknown User')
                    
                    # Prepare comment with file info if file is uploaded (by agent or creator)
                    comment_text = new_comment
                    if uploaded_file is not None and (is_ticket_agent or is_ticket_creator):
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
                    
                    # Clear the comment by incrementing the widget key
                    st.session_state[f'comment_clear_count_{ticket["id"]}'] += 1
                    
                    # st.success("Comment added successfully!")
                    st.rerun()
                else:
                    if not new_comment.strip():
                        st.warning("Please enter a comment.")
                    elif uploaded_file is not None and not (is_ticket_agent or is_ticket_creator):
                        st.warning("Only the assigned agent or ticket creator can attach files.")
        
        st.markdown("---")
        
        # Show attachments section only if attachments exist
        attachments = get_ticket_attachments(int(ticket['id']))
        if not attachments.empty:
            st.subheader("📎 Attachments")
            for idx, attachment in attachments.iterrows():
                # Preview expander with file name only
                with st.expander(f"📄 {attachment['file_name']}", expanded=False):
                    # File details row inside expander
                    col1, col2, col3, col4 = st.columns([3, 1, 2, 1])
                    with col1:
                        st.write(f"**File:** {attachment['file_name']}")
                    with col2:
                        st.write(f"**Size:** {attachment['file_size']} bytes")
                    with col3:
                        st.write(f"**Uploaded:** {attachment['uploaded_at'].strftime('%Y-%m-%d %H:%M')}")
                    with col4:
                        # Download button inside expander
                        file_name, file_type, file_data = download_attachment(attachment['id'])
                        if file_data:
                            st.download_button(
                                label="Download",
                                data=file_data,
                                file_name=file_name,
                                mime=file_type,
                                key=f"dl_{attachment['id']}",
                                use_container_width=True
                            )
                    
                    st.markdown("---")  # Separator between details and preview
                    
                    # File preview content
                    if file_data:
                        # Check if it's an image
                        if file_type and file_type.startswith('image/') or file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                            st.image(file_data, caption=file_name, use_container_width=True)
                        # Check if it's a video
                        elif file_type and file_type.startswith('video/') or file_name.lower().endswith(('.mp4', '.mkv')):
                            st.video(file_data)
                        # Check if it's audio
                        elif file_type and file_type.startswith('audio/') or file_name.lower().endswith('.mp3'):
        
                            st.audio(file_data)
                        # Check if it's a PDF
                        elif file_type == 'application/pdf' or file_name.lower().endswith('.pdf'):
                            # Display PDF using iframe with base64 encoding
                            import base64
                            base64_pdf = base64.b64encode(file_data).decode('utf-8')
                            pdf_display = f"""
                            <iframe src="data:application/pdf;base64,{base64_pdf}" 
                                    width="100%" height="600px" type="application/pdf">
                                <p>Your browser does not support PDFs. 
                                <a href="data:application/pdf;base64,{base64_pdf}" download="{file_name}">Download the PDF</a>.</p>
                            </iframe>
                            """
                            st.markdown(pdf_display, unsafe_allow_html=True)
                            
                        else:
                            st.info(f"Preview not available for {file_type}. Use download button above to view the file.")
                    else:
                        st.error("Could not load file for preview.")
            
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
            search_term = st.text_input("🔍 Search by Ticket No, Order Number", placeholder="🔍 Search by Ticket No, Order Number", key="ticket_search", label_visibility="collapsed")
        
        tickets = fetch_tickets()
        
        # Filter tickets based on search term
        if not tickets.empty and search_term:
            search_term = search_term.lower()
            tickets = tickets[
                tickets['id'].astype(str).str.lower().str.contains(search_term, na=False) |
                tickets['order_number'].astype(str).str.lower().str.contains(search_term, na=False)
        ]
        
        # Create status tabs
        if not tickets.empty:
            # Get logged in user to check if they are an agent
            logged_in_user = st.session_state.get('user_name', 'Unknown User')
            is_agent = logged_in_user in AGENTS
            
            # Get ticket counts by status
            status_counts = tickets['status'].value_counts()
            
            # Create tabs with counts
            tab_labels = []
            
            # Add "My Tickets" tab for agents
            if is_agent:
                my_tickets = tickets[tickets['agent'] == logged_in_user]
                my_tickets_count = len(my_tickets)
                tab_labels.append(f"My Tickets ({my_tickets_count})")
            
            # Add status tabs
            for status in ["Open", "Pending", "Closed", "Resolved"]:
                count = status_counts.get(status, 0)
                tab_labels.append(f"{status} ({count})")
            
            tabs = st.tabs(tab_labels)
            
            # Function to display tickets table
            def display_tickets_table(filtered_tickets, tab_name):
                if not filtered_tickets.empty:
                    # Add top border
                    st.markdown('<hr style="border:2px solid #bbb; margin-top:0; margin-bottom:10px;">', unsafe_allow_html=True)
                    # Header row
                    header_cols = st.columns([1, 1.5, 1.5, 1.5, 1.5, 1, 1, 1.5, 1])
                    header_cols[0].markdown("**Ticket No**")
                    header_cols[1].markdown("**Order Number**")
                    header_cols[2].markdown("**Creator**")
                    header_cols[3].markdown("**Query Type**")
                    header_cols[4].markdown("**Reason**")
                    header_cols[5].markdown("**Priority**")
                    header_cols[6].markdown("**Status**")
                    header_cols[7].markdown("**Ticket Date**")
                    header_cols[8].markdown("**Action**")
                    # Ticket rows with subtle borders
                    for idx, row in filtered_tickets.iterrows():
                        # Add a subtle border between rows
                        if idx > 0:  # Don't add border before first row
                            st.markdown(
                                '<div style="border-top:1px solid #f0f0f0; margin:2px 0;"></div>',
                                unsafe_allow_html=True
                            )
                        cols = st.columns([1, 1.5, 1.5, 1.5, 1.5, 1, 1, 1.5, 1])
                        cols[0].write(row['id'])  # Ticket No
                        cols[1].write(row['order_number'])
                        cols[2].write(row['agent_name'])  # Ticket Creator
                        cols[3].write(row['query_type'])
                        cols[4].write(row['reason'])
                        cols[5].write(row['priority'])  # Priority
                        cols[6].write(row['status'])
                        cols[7].write(str(row['ticket_date']))
                        if cols[8].button("View", key=f"viewbtn_{tab_name}_{row['id']}"):
                            st.session_state.view_ticket_id = row['id']
                            st.rerun()
                    # Add bottom border
                    st.markdown('<hr style="border:2px solid #bbb; margin-top:10px; margin-bottom:0;">', unsafe_allow_html=True)
                else:
                    st.info(f"No {tab_name.lower()} tickets found.")
            
            # Display tickets in each tab
            tab_index = 0
            
            # Show "My Tickets" tab first for agents
            if is_agent:
                with tabs[tab_index]:  # My Tickets
                    my_tickets = tickets[tickets['agent'] == logged_in_user]
                    
                    if not my_tickets.empty:
                        # Create sub-tabs for My Tickets: Open and Pending
                        my_open_tickets = my_tickets[my_tickets['status'] == 'Open']
                        my_pending_tickets = my_tickets[my_tickets['status'] == 'Pending']
                        
                        my_subtab_labels = [
                            f"Open ({len(my_open_tickets)})",
                            f"Pending ({len(my_pending_tickets)})"
                        ]
                        
                        my_subtabs = st.tabs(my_subtab_labels)
                        
                        with my_subtabs[0]:  # My Open Tickets
                            display_tickets_table(my_open_tickets, "MyOpen")
                        
                        with my_subtabs[1]:  # My Pending Tickets
                            display_tickets_table(my_pending_tickets, "MyPending")
                    else:
                        st.info("No tickets assigned to you.")
                tab_index += 1
            
            # Show status tabs
            with tabs[tab_index]:  # Open
                open_tickets = tickets[tickets['status'] == 'Open']
                display_tickets_table(open_tickets, "Open")
            
            with tabs[tab_index + 1]:  # Pending
                pending_tickets = tickets[tickets['status'] == 'Pending']
                display_tickets_table(pending_tickets, "Pending")
            
            with tabs[tab_index + 2]:  # Closed
                closed_tickets = tickets[tickets['status'] == 'Closed']
                display_tickets_table(closed_tickets, "Closed")
            
            with tabs[tab_index + 3]:  # Resolved
                resolved_tickets = tickets[tickets['status'] == 'Resolved']
                display_tickets_table(resolved_tickets, "Resolved")
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
                # Auto-select agent based on logged in user, or default to first agent
                default_agent_index = 0
                if logged_in_user in AGENTS:
                    default_agent_index = AGENTS.index(logged_in_user)
                agent = st.selectbox("Agent", AGENTS, index=default_agent_index)
            
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
                customer_comment = st.text_area("Customer Comment", height=70)
            with col6:
                remark = st.text_area("Remark", height=70)
            
            # Operational Remark and File attachment side by side
            col7, col8 = st.columns(2)
            with col7:
                operational_remark = st.text_area("Operational Remark", height=70, disabled=True, placeholder="Operational remarks can be added after ticket creation")
            with col8:
                uploaded_file = st.file_uploader("📎 Attach File", type=['pdf', 'jpg', 'jpeg', 'png', 'mp4', 'mkv', 'mp3'], key="new_ticket_file_uploader")
            
            status = "Open"  # Always set to Open for new tickets
            
            st.markdown("---")
            
            # Submit and Cancel buttons
            col1, col2, col3 = st.columns([2, 2, 6])
            with col1:
                if st.button("✅ Submit Ticket", use_container_width=True):
                    # Auto-calculate case_count
                    case_count = get_next_case_count(order_number) if order_number else 1
                    # Set operational_remark to empty string for new tickets
                    operational_remark = ""
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