IF OBJECT_ID('dbo.Employee', 'U') IS NOT NULL DROP TABLE dbo.Employee;
IF OBJECT_ID('dbo.Department', 'U') IS NOT NULL DROP TABLE dbo.Department;

CREATE TABLE Department (
    DepartmentID    INT IDENTITY(1,1) PRIMARY KEY,
    DepartmentName  VARCHAR(100) NOT NULL,
    Location        VARCHAR(100) NULL
);

CREATE TABLE Employee (
    EmployeeID      INT IDENTITY(1,1) PRIMARY KEY,
    FirstName       VARCHAR(50) NOT NULL,
    LastName        VARCHAR(50) NOT NULL,
    DepartmentID    INT NOT NULL,
    Salary          DECIMAL(12,2) NOT NULL,
    Bonus           DECIMAL(12,2) NULL,   -- NULL = no bonus awarded
    HireDate        DATE NOT NULL,
    CONSTRAINT FK_Employee_Department
        FOREIGN KEY (DepartmentID) REFERENCES Department(DepartmentID)
);

-- Helpful indexes for the reporting endpoints (Part B)
CREATE INDEX IX_Employee_DepartmentID ON Employee(DepartmentID);
CREATE INDEX IX_Employee_Bonus ON Employee(Bonus);
