# CRM Ticket Management System

A comprehensive Customer Relationship Management (CRM) ticketing system built with Streamlit and PostgreSQL. This application provides a complete solution for managing customer support tickets with advanced features for tracking, collaboration, and file management.

## Features

### 🎫 Ticket Management
- **Create New Tickets**: Streamlined ticket creation with auto-populated fields and duplicate prevention
- **Dynamic Status Tracking**: Open, Pending, Closed, and Resolved status management
- **Automatic Case Counting**: Sequential case numbering for order-based tickets
- **Smart Duplicate Prevention**: Prevents creating multiple open/pending tickets for the same order

### 👥 User Management & Access Control
- **Role-Based Permissions**: Different access levels for ticket creators and assigned agents
- **Agent Assignment**: Tickets can be assigned to specific agents for handling
- **Field-Level Security**: Only authorized users can edit specific fields (operational remarks, status, etc.)

### 📎 File Attachment System
- **Multi-Format Support**: PDF, images (JPG, JPEG, PNG), videos (MP4, MKV), and audio (MP3) files
- **Database Storage**: Files stored securely in PostgreSQL as BYTEA
- **File Preview**: Inline preview for images, PDFs, videos, and audio files
- **Download Functionality**: Easy file download with original filename preservation

### 💬 Communication & Logging
- **Comment System**: Add comments to tickets with real-time updates
- **Comprehensive Audit Trail**: All changes tracked with before/after values
- **Activity Logs**: Detailed logging of all ticket actions and modifications
- **User Attribution**: All actions tracked with user identification

### 🔍 Advanced Filtering & Search
- **Status-Based Tabs**: Organized view by ticket status (Open, Pending, Closed, Resolved)
- **My Tickets**: Personal dashboard for agents showing assigned tickets
- **Search Functionality**: Search by ticket number and order number
- **Agent Sub-Tabs**: Separate views for agent's open and pending tickets

### 📊 Data Management
- **Dynamic Forms**: Configurable dropdowns and cascading field dependencies
- **YAML Configuration**: Externalized dropdown options for easy maintenance
- **Priority Management**: Low, Medium, High priority classification
- **Query Categorization**: Structured query type, reason, and sub-reason classification

### 🎨 User Experience
- **Modern UI**: Clean, responsive interface with intuitive navigation
- **Real-Time Updates**: Instant page refresh after actions
- **Compact Design**: Efficient use of screen space with side-by-side layouts
- **Visual Indicators**: Clear status indicators and action buttons

### 📊 Analytics Dashboard
- **Interactive Charts**: Visual analytics with Plotly charts for status, priority, and trends
- **Key Metrics**: Real-time KPIs including total tickets, resolution times, and status counts
- **Agent Performance**: Detailed performance analytics and resolution rates
- **Time Series Analysis**: Daily ticket creation trends and patterns
- **Data Filtering**: Date range filtering and customizable views
- **Activity Monitoring**: Recent activity feed and audit trail visualization

## Applications

### Main Ticket Management App
```bash
ticket_app.py
```
- Complete ticket CRUD operations
- User authentication and role management
- File attachment and preview system
- Advanced search and filtering

### Analytics Dashboard
```bash
ticket_dashboard.py
```
- Comprehensive analytics and reporting
- Interactive visualizations
- Performance metrics and KPIs
- Real-time data insights

## Database Schema

### tickets TABLE

```sql
CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    ticket_date TIMESTAMP,
    order_number VARCHAR(50),
    agent_name VARCHAR(100),
    qc_on_off BOOLEAN,
    priority VARCHAR(20),
    query_source VARCHAR(50),
    query_type VARCHAR(20),
    reason VARCHAR(100),
    sub_reason VARCHAR(100),
    customer_comment TEXT,
    remark TEXT,
    case_count INTEGER,
    operational_remark TEXT,
    agent VARCHAR(100),
    status VARCHAR(20)
);
```

### ticket_logs TABLE

```sql
CREATE TABLE ticket_logs (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    order_number VARCHAR(50),             
    log_time TIMESTAMP NOT NULL,
    action VARCHAR(50) NOT NULL,          
    comment TEXT,                         
    by_user VARCHAR(100) NOT NULL        
 );
```
### ticket_attachments TABLE

```sql
CREATE TABLE ticket_attachments (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    file_name VARCHAR(255) NOT NULL,              
    file_type VARCHAR(100),                    
    file_size INTEGER,                           
    uploaded_at TIMESTAMP NOT NULL,          
    uploaded_by VARCHAR(100),                      
    file_data BYTEA NOT NULL                       
);
```

---

## 👨‍💻 Developer

**Developed by: Anil**

This CRM Ticket Management System was designed and developed to provide a comprehensive solution for customer support operations. The system combines modern web technologies with robust database management to deliver an efficient and user-friendly ticketing platform.

For questions, suggestions, or contributions, please feel free to reach out.