# crm-sys

### tickets table

```sql
CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    ticket_date DATE,
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


### ticket_logs table

```postgresql
CREATE TABLE ticket_logs (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    order_number VARCHAR(50),             
    log_time TIMESTAMP NOT NULL,
    action VARCHAR(50) NOT NULL,          
    comment TEXT,                         
    by_user VARCHAR(100) NOT NULL        
 );