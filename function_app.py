
"""
All reads/writes to Employee/Department go through these functions — there
is no direct database access from clients. Every SQL statement uses
parameterized queries (pyodbc `?` placeholders), so there is no string
concatenation and no SQL-injection surface.
"""
import json
import logging
import datetime
import functools 
from decimal import Decimal

import azure.functions as func
import pyodbc

from db import get_connection, ConfigError

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json_default(obj):
    """Let json.dumps handle Decimal and date/datetime values from pyodbc."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def json_response(data, status_code=200):
    return func.HttpResponse(
        json.dumps(data, default=_json_default),
        status_code=status_code,
        mimetype="application/json",
    )


def error_response(message, status_code=400):
    return json_response({"error": message}, status_code=status_code)


def row_to_dict(cursor, row):
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))


def rows_to_list(cursor, rows):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


class ValidationError(Exception):
    pass


def handle_request(req_func):
    """
    Wraps a handler so any expected failure maps to the right HTTP status:
    400 for bad input, 404 for missing resources, 500 for anything
    unexpected (logged server-side, generic message to the client).
    """
    @functools.wraps(req_func)
    def wrapper(*args, **kwargs):
        try:
            return req_func(*args, **kwargs)
        except ConfigError as e:
            logging.error(f"Configuration error: {e}")
            return error_response(str(e), 500)
        except ValidationError as e:
            return error_response(str(e), 400)
        except LookupError as e:
            return error_response(str(e), 404)
        except pyodbc.IntegrityError as e:
            logging.warning(f"Integrity error: {e}")
            return error_response(
                "Request violates a database constraint (e.g. unknown DepartmentID).", 400
            )
        except pyodbc.Error as e:
            logging.error(f"Database error: {e}")
            return error_response("A database error occurred.", 500)
        except Exception as e:
            logging.exception("Unexpected error")
            return error_response("An unexpected error occurred.", 500)
    return wrapper


REQUIRED_CREATE_FIELDS = ["FirstName", "LastName", "DepartmentID", "Salary", "HireDate"]


def parse_body(req):
    try:
        return req.get_json()
    except ValueError:
        raise ValidationError("Request body must be valid JSON.")


# ---------------------------------------------------------------------------
# Part A — CRUD
# ---------------------------------------------------------------------------

@app.route(route="employees", methods=["POST"])
@handle_request
def create_employee(req: func.HttpRequest) -> func.HttpResponse:
    body = parse_body(req)
    missing = [f for f in REQUIRED_CREATE_FIELDS if body.get(f) in (None, "")]
    if missing:
        raise ValidationError(f"Missing required field(s): {', '.join(missing)}")

    bonus = body.get("Bonus", None)  # optional — may be left unset

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO Employee (FirstName, LastName, DepartmentID, Salary, Bonus, HireDate)
            OUTPUT INSERTED.EmployeeID
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            body["FirstName"], body["LastName"], body["DepartmentID"],
            body["Salary"], bonus, body["HireDate"],
        )
        new_id = cursor.fetchone()[0]
        conn.commit()

        cursor.execute("SELECT * FROM Employee WHERE EmployeeID = ?", new_id)
        row = cursor.fetchone()
        return json_response(row_to_dict(cursor, row), status_code=201)


@app.route(route="employees/{id:int}", methods=["GET"])
@handle_request
def get_employee(req: func.HttpRequest) -> func.HttpResponse:
    employee_id = req.route_params.get("id")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Employee WHERE EmployeeID = ?", employee_id)
        row = cursor.fetchone()
        if row is None:
            raise LookupError(f"No employee with ID {employee_id}.")
        return json_response(row_to_dict(cursor, row))


@app.route(route="employees", methods=["GET"])
@handle_request
def list_employees(req: func.HttpRequest) -> func.HttpResponse:
    department_id = req.params.get("departmentId")
    with get_connection() as conn:
        cursor = conn.cursor()
        if department_id:
            cursor.execute(
                "SELECT * FROM Employee WHERE DepartmentID = ? ORDER BY EmployeeID",
                department_id,
            )
        else:
            cursor.execute("SELECT * FROM Employee ORDER BY EmployeeID")
        rows = cursor.fetchall()
        return json_response(rows_to_list(cursor, rows))


UPDATABLE_FIELDS = ["FirstName", "LastName", "DepartmentID", "Salary", "Bonus", "HireDate"]


@app.route(route="employees/{id:int}", methods=["PUT"])
@handle_request
def update_employee(req: func.HttpRequest) -> func.HttpResponse:
    employee_id = req.route_params.get("id")
    body = parse_body(req)

    fields = [f for f in UPDATABLE_FIELDS if f in body]
    if not fields:
        raise ValidationError(
            f"Body must include at least one updatable field: {', '.join(UPDATABLE_FIELDS)}"
        )

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM Employee WHERE EmployeeID = ?", employee_id)
        if cursor.fetchone() is None:
            raise LookupError(f"No employee with ID {employee_id}.")

        set_clause = ", ".join(f"{f} = ?" for f in fields)
        values = [body[f] for f in fields] + [employee_id]
        cursor.execute(f"UPDATE Employee SET {set_clause} WHERE EmployeeID = ?", values)
        conn.commit()

        cursor.execute("SELECT * FROM Employee WHERE EmployeeID = ?", employee_id)
        row = cursor.fetchone()
        return json_response(row_to_dict(cursor, row))


@app.route(route="employees/{id:int}", methods=["DELETE"])
@handle_request
def delete_employee(req: func.HttpRequest) -> func.HttpResponse:
    employee_id = req.route_params.get("id")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM Employee WHERE EmployeeID = ?", employee_id)
        if cursor.fetchone() is None:
            raise LookupError(f"No employee with ID {employee_id}.")

        cursor.execute("DELETE FROM Employee WHERE EmployeeID = ?", employee_id)
        conn.commit()
        return func.HttpResponse(status_code=204)


# ---------------------------------------------------------------------------
# Part B — Compensation reporting
# ---------------------------------------------------------------------------

@app.route(route="reports/total-bonus", methods=["GET"])
@handle_request
def report_total_bonus(req: func.HttpRequest) -> func.HttpResponse:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(COALESCE(Bonus, 0)) AS TotalBonus FROM Employee")
        row = cursor.fetchone()
        total = row[0] if row[0] is not None else 0
        return json_response({"TotalBonus": total})


@app.route(route="reports/no-bonus", methods=["GET"])
@handle_request
def report_no_bonus(req: func.HttpRequest) -> func.HttpResponse:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM Employee WHERE Bonus IS NULL ORDER BY EmployeeID"
        )
        rows = cursor.fetchall()
        return json_response(rows_to_list(cursor, rows))


@app.route(route="reports/bonus-percentage", methods=["GET"])
@handle_request
def report_bonus_percentage(req: func.HttpRequest) -> func.HttpResponse:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT EmployeeID, FirstName, LastName, Salary, Bonus,
                   CAST(ROUND((Bonus / Salary) * 100.0, 2) AS DECIMAL(5,2)) AS BonusPercentage
            FROM Employee
            WHERE Bonus IS NOT NULL
            ORDER BY EmployeeID
            """
        )
        rows = cursor.fetchall()
        return json_response(rows_to_list(cursor, rows))


@app.route(route="reports/departments-bonus-exceeds-avg-salary", methods=["GET"])
@handle_request
def report_departments_bonus_exceeds_avg_salary(req: func.HttpRequest) -> func.HttpResponse:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT d.DepartmentID, d.DepartmentName,
                   SUM(COALESCE(e.Bonus, 0)) AS TotalBonus,
                   AVG(e.Salary) AS AvgSalary
            FROM Department d
            JOIN Employee e ON e.DepartmentID = d.DepartmentID
            GROUP BY d.DepartmentID, d.DepartmentName
            HAVING SUM(COALESCE(e.Bonus, 0)) > AVG(e.Salary)
            ORDER BY d.DepartmentID
            """
        )
        rows = cursor.fetchall()
        return json_response(rows_to_list(cursor, rows))


@app.route(route="reports/employees-ranked-by-bonus", methods=["GET"])
@handle_request
def report_employees_ranked_by_bonus(req: func.HttpRequest) -> func.HttpResponse:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT EmployeeID, FirstName, LastName, Bonus
            FROM Employee
            ORDER BY CASE WHEN Bonus IS NULL THEN 1 ELSE 0 END, Bonus DESC
            """
        )
        rows = cursor.fetchall()
        return json_response(rows_to_list(cursor, rows))


@app.route(route="reports/highest-salary", methods=["GET"])
@handle_request
def report_highest_salary(req: func.HttpRequest) -> func.HttpResponse:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT TOP 1 * FROM Employee ORDER BY Salary DESC, EmployeeID ASC"
        )
        highest_salary_row = cursor.fetchone()
        highest_salary_employee = row_to_dict(cursor, highest_salary_row)

        cursor.execute(
            "SELECT TOP 1 * FROM Employee ORDER BY (Salary + COALESCE(Bonus, 0)) DESC, EmployeeID ASC"
        )
        highest_comp_row = cursor.fetchone()
        highest_comp_employee = row_to_dict(cursor, highest_comp_row)

        same_person = (
            highest_salary_employee["EmployeeID"] == highest_comp_employee["EmployeeID"]
        )

        return json_response({
            "HighestBaseSalaryEmployee": highest_salary_employee,
            "HighestTotalCompensationEmployee": highest_comp_employee,
            "SamePersonHoldsBoth": same_person,
        })


# ---------------------------------------------------------------------------
# Part C — Default bonus (optional feature)
# ---------------------------------------------------------------------------
#
# Design decision: computed at READ TIME via SQL COALESCE(Bonus, Salary * 0.05),
# gated behind an opt-in query flag (applyDefaultBonus=true) — not written
# into the table. See README "Design decisions" for the full reasoning.

DEFAULT_BONUS_RATE = 0.05


@app.route(route="employees/{id:int}/effective-bonus", methods=["GET"])
@handle_request
def get_effective_bonus(req: func.HttpRequest) -> func.HttpResponse:
    employee_id = req.route_params.get("id")
    apply_default = req.params.get("applyDefaultBonus", "false").lower() == "true"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT EmployeeID, Salary, Bonus FROM Employee WHERE EmployeeID = ?",
            employee_id,
        )
        row = cursor.fetchone()
        if row is None:
            raise LookupError(f"No employee with ID {employee_id}.")

        employee_id_val, salary, raw_bonus = row
        default_applied = apply_default and raw_bonus is None

        if raw_bonus is not None:
            effective_bonus = raw_bonus
        elif apply_default:
            effective_bonus = round(float(salary) * DEFAULT_BONUS_RATE, 2)
        else:
            effective_bonus = 0

        return json_response({
            "EmployeeID": employee_id_val,
            "RawBonus": raw_bonus,
            "EffectiveBonus": effective_bonus,
            "DefaultBonusApplied": default_applied,
        })
