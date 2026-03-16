# Database Basics

## What is a Database?

A database is an organized collection of data stored and accessed electronically. Databases are managed by Database Management Systems (DBMS) that allow users to create, read, update, and delete data efficiently.

## Types of Databases

### Relational Databases (SQL)

Store data in tables with rows and columns. Each table has a defined schema. Examples: PostgreSQL, MySQL, SQLite.

### NoSQL Databases

Store data in flexible formats. Types include:
- **Document stores**: MongoDB (JSON-like documents)
- **Key-value stores**: Redis (simple key-value pairs)
- **Graph databases**: Neo4j (relationships between data)

## SQL Fundamentals

SQL (Structured Query Language) is the standard language for working with relational databases.

### Creating Tables

```sql
CREATE TABLE students (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    enrollment_date DATE DEFAULT CURRENT_DATE
);
```

### Basic Queries

- **SELECT**: Retrieve data — `SELECT name, email FROM students;`
- **INSERT**: Add data — `INSERT INTO students (name, email) VALUES ('Alice', 'alice@edu.com');`
- **UPDATE**: Modify data — `UPDATE students SET email = 'new@edu.com' WHERE id = 1;`
- **DELETE**: Remove data — `DELETE FROM students WHERE id = 1;`

### Filtering and Sorting

- **WHERE**: Filter rows — `SELECT * FROM students WHERE name LIKE 'A%';`
- **ORDER BY**: Sort results — `SELECT * FROM students ORDER BY name ASC;`
- **LIMIT**: Restrict result count — `SELECT * FROM students LIMIT 10;`

### Joins

Combine data from multiple tables:

```sql
SELECT students.name, courses.title
FROM students
JOIN enrollments ON students.id = enrollments.student_id
JOIN courses ON enrollments.course_id = courses.id;
```

## Database Design Principles

- **Primary Keys**: Unique identifier for each row
- **Foreign Keys**: Link between tables, enforce referential integrity
- **Normalization**: Organize data to reduce redundancy
- **Indexes**: Speed up queries on frequently searched columns
