<<<<<<< HEAD
# employee-compensation-service
=======
# Employee Compensation Service

Azure Functions (Python, HTTP-triggered) backed by Azure SQL Database. All reads/writes go through this Functions layer — there is no direct database access from clients.

## Tech stack

- **Runtime**: Azure Functions, Python v2 programming model  
- **Database**: Azure SQL Database (SQL Server T-SQL syntax)  
- **DB driver**: `pyodbc`

## Project structure

employee-compensation-service/

├── function\_app.py              \# all HTTP-triggered functions

├── db.py                        \# connection helper (reads secret from env)

├── requirements.txt

├── host.json

├── local.settings.json.example  \# copy to local.settings.json and fill in

├── .gitignore                   \# keeps local.settings.json out of git

└── sql/

    ├── schema.sql                \# CREATE TABLE for Department, Employee

    └── seed.sql                  \# sample data incl. NULL bonuses

## Setup & running locally (Windows / PowerShell)

1. **Prerequisites**  
     
   - Python 3.11  
   - [Azure Functions Core Tools v4](https://learn.microsoft.com/azure/azure-functions/functions-run-local) (only used to run `func start` locally — everything else is Portal)  
   - ODBC Driver 18 for SQL Server installed locally  
   - An Azure SQL Database (free tier is enough) — created via the **Portal**, see [Azure Free Account](https://azure.microsoft.com/free/)

   

2. **Create the database (Portal)**  
     
   - Portal → "SQL databases" → Create → new database `EmployeeCompensationDB`, new server, Serverless/Gen5/1 vCore compute tier, minimum storage (1.3 GB — no need for more with 15 rows of seed data).  
   - Server → **Security → Networking** → allow your client IP \+ "Allow Azure services and resources to access this server".  
   - Run `sql/schema.sql` then `sql/seed.sql` in the Portal's **Query editor**.

   

3. **Configure secrets**  
     
   cp local.settings.json.example local.settings.json  
     
   Edit `local.settings.json` and fill in `SQL_CONNECTION_STRING` with your database's connection string (Portal → your database → **Connection strings** blade → ODBC tab), replacing every `<...>` placeholder (server, database, user, password) with real values. This file is git-ignored and never committed — **no secrets are hardcoded in source** (Part C requirement).  
     
4. **Install dependencies & run**  
     
   python \-m venv .venv  
     
   .\\.venv\\Scripts\\Activate.ps1  
     
   python \-m pip install \--force-reinstall \--no-cache-dir \-r requirements.txt  
     
   func start  
     
   Functions will be available at `http://localhost:7071/api/...` (locally, function-key auth is not enforced, so no `?code=` is needed.)  
     
   Run `func start` in its own terminal and leave it running — open a **second** terminal for testing endpoints (see below).  
     
5. **Deploying to Azure (optional, Portal)**  
     
   - Portal → Create a resource → **Function App** → Runtime stack: Python 3.11, Region: same as your DB.  
   - Once created: **Deployment Center** → connect your GitHub repo (or use the built-in **VS Code Azure Functions extension** "Deploy" button — also GUI-driven, no CLI).  
   - Function App → **Configuration** → Application settings → add `SQL_CONNECTION_STRING` there (never in source).  
   - Test with `?code=<key>` from the Function App's **App keys** blade.

## Testing endpoints on Windows (PowerShell)

PowerShell's built-in `curl` is an alias for `Invoke-WebRequest`, which does **not** understand curl's `-X` / `-H` / `-d` flags, and hides the response body on non-2xx errors. Use one of these instead:

**Option A — `curl.exe` (the real curl), one line, escaped quotes:**

curl.exe \-X POST http://localhost:7071/api/employees \-H "Content-Type: application/json" \-d '{\\"FirstName\\":\\"Test\\",\\"LastName\\":\\"User\\",\\"DepartmentID\\":1,\\"Salary\\":700000,\\"HireDate\\":\\"2024-01-01\\"}'

**Option B — `Invoke-RestMethod` (PowerShell-native, recommended):**

\# GET

Invoke-RestMethod http://localhost:7071/api/employees

\# POST

$newEmp \= @{

    FirstName    \= "Test"

    LastName     \= "User"

    DepartmentID \= 1

    Salary       \= 700000

    HireDate     \= "2024-01-01"

} | ConvertTo-Json

$created \= Invoke-RestMethod \-Uri http://localhost:7071/api/employees \-Method POST \-ContentType "application/json" \-Body $newEmp

$created.EmployeeID   \# capture the real new ID — don't assume it

\# PUT

$update \= @{ Bonus \= 35000 } | ConvertTo-Json

Invoke-RestMethod \-Uri "http://localhost:7071/api/employees/$($created.EmployeeID)" \-Method PUT \-ContentType "application/json" \-Body $update

\# DELETE

Invoke-RestMethod \-Uri "http://localhost:7071/api/employees/$($created.EmployeeID)" \-Method DELETE

If a call errors and you need the actual response body (not just "(404) Not Found"):

try {

    Invoke-RestMethod \-Uri \<url\> \-Method \<verb\>

} catch {

    $reader \= New-Object System.IO.StreamReader($\_.Exception.Response.GetResponseStream())

    $reader.ReadToEnd()

}

## Troubleshooting log (issues actually hit during setup)

| Symptom | Cause | Fix |
| :---- | :---- | :---- |
| `Function wrapper does not have a unique function name` | `handle_request`'s inner `wrapper()` had no `functools.wraps(req_func)`, so every decorated route collapsed to the same internal name `wrapper` | Add `import functools` and `@functools.wraps(req_func)` directly above `def wrapper(...)` in `function_app.py` |
| `ModuleNotFoundError: No module named 'pyodbc'` even after `pip install` | venv was recreated after the original install; old `pip` cache reported "already satisfied" against a stale venv | `python -m pip install --force-reinstall --no-cache-dir -r requirements.txt`, then confirm with `python -m pip show pyodbc` |
| `SyntaxError: invalid syntax (db.py, line 1)` — `import osimport pyodbc` | Two import lines got merged onto one during a copy/paste | Ensure `db.py` starts with `import os` and `import pyodbc` on separate lines |
| `Client with IP address 'X.X.X.X' is not allowed to access the server` — recurring with a **different IP almost every request** | Mobile/ISP CGNAT rotating the public IP per-connection (common on Indian mobile data) | Add a temporary firewall **range** rule (e.g. `152.58.0.0`–`152.59.255.255`) covering the pool instead of single IPs; **delete the range rule when done for the day**. Prefer wifi over mobile data when possible — wifi usually holds one stable IP. |
| PowerShell `curl -X POST ... -H ... -d ...` throws `ParameterBindingException` / `-H not recognized` | PowerShell's `curl` \= `Invoke-WebRequest`, doesn't support curl flags; `\` line continuation is bash-only | Use `curl.exe` explicitly, or switch to `Invoke-RestMethod` (see Testing section above) |
| `Invoke-RestMethod` / `Invoke-WebRequest` shows only `(404) Not Found` with no detail | These cmdlets swallow the response body on error by default | Wrap in `try/catch` and read `$_.Exception.Response.GetResponseStream()` (see Testing section) |
| All endpoints suddenly 404, including previously-working `GET /api/employees` | The `func start` host had stopped/crashed in its terminal, or tests were run in the same terminal as `func start` (which blocks it) | Confirm `func start`'s terminal still shows the route list; always test from a **second** terminal |
| `SQL_CONNECTION_STRING is not set` / connection string still has `<your-server>` etc. | `local.settings.json` copied from the `.example` but placeholders never replaced | Fill in real server, database, user, and password — no `<...>` left |

## API reference

### Part A — CRUD

| Method | Route | Description |
| :---- | :---- | :---- |
| POST | `/api/employees` | Create an employee (`Bonus` optional) |
| GET | `/api/employees/{id}` | Get one employee |
| GET | `/api/employees?departmentId={id}` | List employees, optional dept filter |
| PUT | `/api/employees/{id}` | Update an employee (partial body) |
| DELETE | `/api/employees/{id}` | Delete an employee |

Example create request body:

{

  "FirstName": "Rohan",

  "LastName": "Bhatt",

  "DepartmentID": 1,

  "Salary": 850000.00,

  "Bonus": null,

  "HireDate": "2024-01-15"

}

### Part B — Compensation reporting

| Method | Route | Description |
| :---- | :---- | :---- |
| GET | `/api/reports/total-bonus` | Total bonus paid company-wide (NULL → 0\) |
| GET | `/api/reports/no-bonus` | Employees who never received a bonus |
| GET | `/api/reports/bonus-percentage` | Bonus as % of salary, per employee with a bonus |
| GET | `/api/reports/departments-bonus-exceeds-avg-salary` | Departments where total bonus \> avg salary |
| GET | `/api/reports/employees-ranked-by-bonus` | All employees ranked by bonus, no-bonus ranked last |
| GET | `/api/reports/highest-salary` | Highest base salary employee \+ whether they also lead total comp |

### Part C — Default bonus (optional feature, implemented)

| Method | Route | Description |
| :---- | :---- | :---- |
| GET | `/api/employees/{id}/effective-bonus?applyDefaultBonus=true` | Returns bonus with the 5%-of-salary default applied for employees who have none |

## Design decisions (for the interview)

**Why Functions-only DB access?** Keeps a single, auditable, testable choke point for all data access — consistent validation, consistent error handling, and no client ever needs direct DB credentials.

**How NULL bonuses are handled**

- Treated as `0` for aggregate sums (`COALESCE(Bonus, 0)`).  
- Treated as "excluded" for percentage calculations (can't divide against a bonus that doesn't exist).  
- Treated as "last place, not absent" for ranking — `ORDER BY CASE WHEN Bonus IS NULL THEN 1 ELSE 0 END, Bonus DESC`.

**Default 5% bonus — read-time vs. write-time** Implemented at **read time** via SQL `COALESCE(Bonus, Salary * 0.05)`, exposed as an opt-in query flag (`applyDefaultBonus=true`) rather than changing the stored value. Reasoning:

1. `Bonus IS NULL` is meaningful business data ("no bonus awarded") — overwriting it with a computed number destroys that signal permanently.  
2. If the default percentage changes later, a read-time calculation updates everywhere instantly; a write-time value needs a backfill migration across the whole table.  
3. Part B's reporting endpoints depend on being able to distinguish "no bonus" from "small bonus" — conflating the two at the storage layer would make several of those endpoints meaningless.

The trade-off: read-time calculation adds a small amount of query complexity and can't be indexed the way a materialized column could. For this dataset's scale that's a non-issue; at very large scale a computed persisted column would be the alternative worth discussing.

**Security / production readiness**

- No hardcoded secrets — `SQL_CONNECTION_STRING` comes from environment / Application Settings only (`local.settings.json` is git-ignored).  
- All queries are parameterized (`?` placeholders via `pyodbc`) — no string concatenation, so no SQL injection surface.  
- Errors are caught and mapped to appropriate HTTP status codes: `400` for bad input/constraint violations, `404` for missing resources, `500` for unexpected failures (logged server-side, generic message to the client).  
- SQL firewall access is IP-scoped; broad temporary ranges added during development (e.g. to work around ISP CGNAT) are removed once testing is complete, not left open in the deployed configuration.

## SQL scripts

See `sql/schema.sql` (DDL) and `sql/seed.sql` (sample data, includes employees with `Bonus = NULL` across multiple departments so every reporting endpoint has real cases to exercise).  
>>>>>>> feb0395 (Employee Compensation Service - Azure Functions + Azure SQL)
