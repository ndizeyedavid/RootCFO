-- Active: 1785112301079@@127.0.0.1@3306@alu_db
CREATE DATABASE IF NOT EXISTS rootcfo;

-- Select database
USE rootcfo;

-- Companies table
CREATE TABLE IF NOT EXISTS companies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255),
    address TEXT,
    business_hours VARCHAR(100) DEFAULT 'Mon-Fri 8:00-17:00',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'viewer') DEFAULT 'admin',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    date DATE NOT NULL,
    description VARCHAR(500),
    amount DECIMAL(15, 2) NOT NULL,
    account VARCHAR(100),
    person VARCHAR(100),
    source_file VARCHAR(255),
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- Anomalies table
CREATE TABLE IF NOT EXISTS anomalies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    transaction_id INT,
    anomaly_type ENUM(
        'duplicate',
        'off_hours',
        'benford_deviation',
        'vendor_pattern',
        'amount_threshold',
        'ai_flagged'
    ) NOT NULL,
    severity ENUM('critical', 'warning', 'info') DEFAULT 'warning',
    description TEXT NOT NULL,
    ai_analysis TEXT,
    flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE,
    FOREIGN KEY (transaction_id) REFERENCES transactions (id) ON DELETE SET NULL
);