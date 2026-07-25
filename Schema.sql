-- Active: 1784986771712@@mysql-225821d8-test-db-102234.j.aivencloud.com@27766@rootcfo
-- Active: 1784281163654@@mysql-168a8dfe-alustudent-5968.b.aivencloud.com@17422@defaultdb
-- Create the database
-- Create database
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