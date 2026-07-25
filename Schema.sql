-- Active: 1784986771712@@mysql-225821d8-test-db-102234.j.aivencloud.com@27766@rootcfo
-- Active: 1784281163654@@mysql-168a8dfe-alustudent-5968.b.aivencloud.com@17422@defaultdb
-- Create the database
CREATE DATABASE IF NOT EXISTS rootcfo;

-- Select the database
USE rootcfo;

-- =========================
-- Companies Table
-- =========================
CREATE TABLE IF NOT EXISTS companies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255),
    address TEXT,
    business_hours VARCHAR(100) DEFAULT 'Mon-Fri 8:00-17:00',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);