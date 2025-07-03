# crm-sys

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

