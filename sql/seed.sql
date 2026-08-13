
-- Includes employees with Bonus = NULL across multiple departments so every
-- reporting endpoint in Part B has real cases to exercise.

SET IDENTITY_INSERT Department ON;
INSERT INTO Department (DepartmentID, DepartmentName, Location) VALUES
    (1, 'Engineering', 'Pune'),
    (2, 'Sales',       'Mumbai'),
    (3, 'HR',          'Pune'),
    (4, 'Finance',     'Bengaluru'),
    (5, 'Marketing',   'Mumbai');
SET IDENTITY_INSERT Department OFF;

SET IDENTITY_INSERT Employee ON;
INSERT INTO Employee (EmployeeID, FirstName, LastName, DepartmentID, Salary, Bonus, HireDate) VALUES
    (1,  'Aarav',   'Sharma', 1, 1200000.00, 120000.00, '2021-03-15'),
    (2,  'Diya',    'Patel',  1,  950000.00, NULL,       '2022-07-01'),
    (3,  'Ishaan',  'Kumar',  2,  800000.00, NULL,       '2023-01-10'),
    (4,  'Ananya',  'Singh',  2,  900000.00,  90000.00, '2020-11-20'),
    (5,  'Vivaan',  'Reddy',  3,  700000.00, NULL,       '2023-05-05'),
    (6,  'Myra',    'Iyer',   3,  750000.00, NULL,       '2022-09-18'),
    (7,  'Kabir',   'Mehta',  1, 1500000.00, 200000.00, '2019-02-01'),
    (8,  'Zara',    'Khan',   4,  850000.00, NULL,       '2023-03-22'),
    (9,  'Reyansh', 'Nair',   4,  980000.00, 110000.00, '2021-08-14'),
    (10, 'Saanvi',  'Rao',    5,  820000.00,  70000.00, '2022-02-28'),
    (11, 'Advait',  'Joshi',  5,  770000.00, NULL,       '2023-10-01'),
    (12, 'Aadhya',  'Gupta',  1, 1100000.00, 130000.00, '2020-06-10'),
    (13, 'Vihaan',  'Verma',  2,  890000.00,  95000.00, '2021-12-05'),
    (14, 'Anika',   'Menon',  3,  710000.00,  60000.00, '2022-04-17'),
    (15, 'Arjun',   'Pillai', 4,  940000.00, 105000.00, '2019-09-09');
SET IDENTITY_INSERT Employee OFF;
