"""Admin routes"""


from flask import (Blueprint, flash, session, request, redirect, url_for, render_template)

from database import get_db_connection
from utils import config
from utils.admin import create_user, authenticate_user, admin_required
from utils.crew import get_current_user
from utils.scoring import recalculate_crew_scores

admin_routes = Blueprint("admin_routes", __name__, template_folder="templates")

# ===================================
# Authentication Routes
# ===================================


@admin_routes.route("/login", methods=["GET", "POST"])
def login():
    """User and admin login page"""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Check for admin login (backward compatibility)
        if username.lower() == "admin" and password == config.ADMIN_PASSWORD:
            # Create admin user if it doesn't exist
            conn = get_db_connection()
            admin_user = conn.execute(
                """
                SELECT * FROM users WHERE username = 'admin' AND is_admin = TRUE
            """
            ).fetchone()

            if not admin_user:
                admin_id = create_user("admin", config.ADMIN_PASSWORD, is_admin=True)
                admin_user = conn.execute(
                    "SELECT * FROM users WHERE id = ?", (admin_id,)
                ).fetchone()

            conn.close()

            if admin_user:
                session["user_id"] = admin_user["id"]
                # Update last login
                conn = get_db_connection()
                conn.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                    (admin_user["id"],),
                )
                conn.commit()
                conn.close()

                flash("Successfully logged in as admin", "success")
                return redirect(url_for("admin_routes.admin"))

        # Regular user authentication
        elif username and password:
            user = authenticate_user(username, password)
            if user:
                session["user_id"] = user["id"]
                # Update last login
                conn = get_db_connection()
                conn.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                    (user["id"],),
                )
                conn.commit()
                conn.close()

                if user["is_admin"]:
                    flash("Successfully logged in as admin", "success")
                    return redirect(url_for("admin_routes.admin"))
                else:
                    flash(f"Welcome back, {user['username']}!", "success")
                    # Redirect to preferences for their crew
                    return redirect(url_for("base_routes.preferences", crew_id=user["crew_id"]))
            else:
                flash("Invalid username or password", "error")
        else:
            flash("Please enter both username and password", "error")

    return render_template("login.html")


@admin_routes.route("/logout")
def logout():
    """Logout and clear session"""
    session.clear()  # Clear all session data
    flash("Successfully logged out", "success")
    return redirect(url_for("base_routes.index"))


@admin_routes.route("/admin")
@admin_required
def admin():
    """Admin page for managing crew members"""
    selected_crew_id = request.args.get("crew_id", type=int)

    conn = get_db_connection()

    # Get all crews
    crews = conn.execute("SELECT * FROM crews ORDER BY crew_name").fetchall()

    selected_crew = None
    crew_members = []

    if selected_crew_id:
        # Get selected crew info
        selected_crew = conn.execute(
            "SELECT * FROM crews WHERE id = ?", (selected_crew_id,)
        ).fetchone()

        if selected_crew:
            # Get crew members with survey completion status
            crew_members = conn.execute(
                """
                SELECT cm.*,
                       CASE
                           WHEN EXISTS (
                               SELECT 1 FROM program_scores ps
                               WHERE ps.crew_member_id = cm.id
                           ) THEN 1
                           ELSE 0
                       END as survey_completed
                FROM crew_members cm
                WHERE cm.crew_id = ?
                ORDER BY cm.member_number
            """,
                (selected_crew_id,),
            ).fetchall()

    conn.close()

    return render_template(
        "admin.html",
        crews=crews,
        selected_crew=selected_crew,
        selected_crew_id=selected_crew_id,
        crew_members=crew_members,
    )


@admin_routes.route("/admin/edit_crew", methods=["POST"])
@admin_required
def edit_crew():
    """Edit crew details"""
    crew_id = request.form.get("crew_id", type=int)
    crew_name = request.form.get("crew_name", "").strip()
    crew_size = request.form.get("crew_size", type=int)

    if not crew_id or not crew_name:
        flash("Crew ID and name are required.", "error")
        return redirect(url_for("admin_routes.admin"))

    conn = get_db_connection()

    try:
        conn.execute(
            """
            UPDATE crews
            SET crew_name = ?, crew_size = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (crew_name, crew_size, crew_id),
        )

        conn.commit()
        flash(f'Crew "{crew_name}" updated successfully!', "success")

    except Exception as e:
        conn.rollback()
        flash(f"Error updating crew: {str(e)}", "error")
    finally:
        conn.close()

    return redirect(url_for("admin_routes.admin", crew_id=crew_id))


@admin_routes.route("/admin/add_member", methods=["POST"])
def add_member():
    """Add a new crew member"""
    crew_id = request.form.get("crew_id", type=int)
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    age = request.form.get("age", type=int)
    skill_level = request.form.get("skill_level", 6, type=int)
    redirect_to = request.form.get(
        "redirect_to", "admin"
    )  # Default to admin for backward compatibility

    if not crew_id or not name:
        flash("Crew and name are required.", "error")
        if redirect_to == "preferences":
            return redirect(url_for("base_routes.preferences"))
        return redirect(url_for("admin_routes.admin", crew_id=crew_id))

    conn = get_db_connection()

    try:
        # Get next member number for this crew
        max_member = conn.execute(
            "SELECT MAX(member_number) as max_num FROM crew_members WHERE crew_id = ?",
            (crew_id,),
        ).fetchone()
        member_number = (max_member["max_num"] or 0) + 1

        # Insert new crew member with email
        conn.execute(
            """
            INSERT INTO crew_members (crew_id, member_number, name, email, age, skill_level)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (crew_id, member_number, name, email, age, skill_level),
        )

        # If email is provided, we could store it in a separate table or extend the crew_members table
        # For now, let's extend the crew_members table to include email

        conn.commit()
        flash(f'Crew member "{name}" added successfully!', "success")

        # Note: No need to recalculate scores here since new member has no program scores yet

    except Exception as e:
        conn.rollback()
        flash(f"Error adding crew member: {str(e)}", "error")
    finally:
        conn.close()

    # Redirect based on the source page
    if redirect_to == "preferences":
        return redirect(url_for("base_routes.preferences"))
    return redirect(url_for("admin_routes.admin", crew_id=crew_id))


@admin_routes.route("/admin/edit_member", methods=["POST"])
def edit_member():
    """Edit an existing crew member"""
    member_id = request.form.get("member_id", type=int)
    crew_id = request.form.get("crew_id", type=int)
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    age = request.form.get("age", type=int)
    skill_level = request.form.get("skill_level", 6, type=int)

    if not member_id or not name:
        flash("Member ID and name are required.", "error")
        return redirect(url_for("admin_routes.admin", crew_id=crew_id))

    conn = get_db_connection()

    try:
        conn.execute(
            """
            UPDATE crew_members
            SET name = ?, email = ?, age = ?, skill_level = ?
            WHERE id = ?
        """,
            (name, email, age, skill_level, member_id),
        )

        conn.commit()

        # Recalculate crew scores after member info update (in case skill level affects scoring)
        try:
            recalculate_crew_scores(crew_id)
            flash(
                f'Crew member "{name}" updated successfully! Crew scores have been updated.',
                "success",
            )
        except Exception as e:
            flash(
                f'Crew member "{name}" updated, but there was an issue updating crew scores: {str(e)}',
                "warning",
            )

    except Exception as e:
        conn.rollback()
        flash(f"Error updating crew member: {str(e)}", "error")
    finally:
        conn.close()

    return redirect(url_for("admin_routes.admin", crew_id=crew_id))


@admin_routes.route("/admin/delete_member", methods=["POST"])
def delete_member():
    """Delete a crew member and all associated data"""
    member_id = request.form.get("member_id", type=int)
    crew_id = request.form.get("crew_id", type=int)
    redirect_to = request.form.get(
        "redirect_to", "admin"
    )  # Default to admin for backward compatibility

    if not member_id:
        flash("Member ID is required.", "error")
        if redirect_to == "preferences":
            return redirect(url_for("base_routes.preferences"))
        return redirect(url_for("admin_routes.admin", crew_id=crew_id))

    conn = get_db_connection()

    try:
        # Delete program scores first (foreign key constraint)
        conn.execute(
            "DELETE FROM program_scores WHERE crew_member_id = ?", (member_id,)
        )

        # Delete the crew member
        cursor = conn.execute("DELETE FROM crew_members WHERE id = ?", (member_id,))

        if cursor.rowcount > 0:
            conn.commit()

            # Recalculate crew scores after member deletion
            try:
                recalculate_crew_scores(crew_id)
                flash(
                    "Crew member deleted successfully! Crew scores have been updated.",
                    "success",
                )
            except Exception as e:
                flash(
                    f"Crew member deleted, but there was an issue updating crew scores: {str(e)}",
                    "warning",
                )
        else:
            flash("Crew member not found.", "error")

    except Exception as e:
        conn.rollback()
        flash(f"Error deleting crew member: {str(e)}", "error")
    finally:
        conn.close()

    # Redirect based on the source page
    if redirect_to == "preferences":
        return redirect(url_for("base_routes.preferences"))
    return redirect(url_for("admin_routes.admin", crew_id=crew_id))


@admin_routes.route("/admin/delete_all_members", methods=["POST"])
def delete_all_members():
    """Delete all crew members and their associated data"""
    crew_id = request.form.get("crew_id", type=int)

    if not crew_id:
        flash("Crew ID is required.", "error")
        return redirect(url_for("base_routes.preferences"))

    conn = get_db_connection()

    try:
        # Get count of members to be deleted for feedback
        member_count = conn.execute(
            "SELECT COUNT(*) as count FROM crew_members WHERE crew_id = ?", (crew_id,)
        ).fetchone()["count"]

        if member_count == 0:
            flash("No crew members to delete.", "info")
            return redirect(url_for("base_routes.preferences"))

        # Delete program scores first (foreign key constraint)
        conn.execute("DELETE FROM program_scores WHERE crew_id = ?", (crew_id,))

        # Delete all crew members for this crew
        conn.execute("DELETE FROM crew_members WHERE crew_id = ?", (crew_id,))

        conn.commit()

        # Recalculate crew scores after all member deletion (will result in no scores)
        try:
            recalculate_crew_scores(crew_id)
            flash(
                f"All {member_count} crew members deleted successfully! All program scores have been cleared.",
                "success",
            )
        except Exception as e:
            flash(
                f"All crew members deleted, but there was an issue updating crew scores: {str(e)}",
                "warning",
            )

    except Exception as e:
        conn.rollback()
        flash(f"Error deleting crew members: {str(e)}", "error")
    finally:
        conn.close()

    return redirect(url_for("base_routes.preferences"))


# ===================================
# User Management Routes (Admin Only)
# ===================================


@admin_routes.route("/admin/users")
@admin_required
def admin_users():
    """Admin page for managing user accounts"""
    conn = get_db_connection()

    # Get all users with their crew information
    users = conn.execute(
        """
        SELECT u.*, c.crew_name
        FROM users u
        LEFT JOIN crews c ON u.crew_id = c.id
        ORDER BY u.is_admin DESC, u.username
    """
    ).fetchall()

    # Get all crews for the dropdown
    crews = conn.execute("SELECT * FROM crews ORDER BY crew_name").fetchall()

    conn.close()

    return render_template("admin_users.html", users=users, crews=crews)


@admin_routes.route("/admin/users/create", methods=["POST"])
@admin_required
def admin_create_user():
    """Create a new user account"""
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    crew_id = request.form.get("crew_id", type=int)
    is_admin = "is_admin" in request.form

    # Validation
    if not username:
        flash("Username is required", "error")
        return redirect(url_for("admin_routes.admin_users"))

    if not password:
        flash("Password is required", "error")
        return redirect(url_for("admin_routes.admin_users"))

    if not is_admin and not crew_id:
        flash("Regular users must be assigned to a crew", "error")
        return redirect(url_for("admin_routes.admin_users"))

    if is_admin and crew_id:
        flash("Admin users cannot be assigned to a specific crew", "error")
        return redirect(url_for("admin_routes.admin_users"))

    # Create user
    user_id = create_user(
        username, password, crew_id if not is_admin else None, is_admin
    )

    if user_id:
        flash(f'User "{username}" created successfully!', "success")
    else:
        flash(f'Error creating user "{username}" - username may already exist', "error")

    return redirect(url_for("admin_routes.admin_users"))


@admin_routes.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    """Delete a user account"""
    conn = get_db_connection()

    try:
        # Get user info first
        user = conn.execute(
            "SELECT username FROM users WHERE id = ?", (user_id,)
        ).fetchone()

        if user:
            # Don't allow deleting the current admin user
            current_user = get_current_user()
            if user_id == current_user["id"]:
                flash("Cannot delete your own account while logged in", "error")
                return redirect(url_for("admin_routes.admin_users"))

            # Delete the user
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            flash(f'User "{user["username"]}" deleted successfully', "success")
        else:
            flash("User not found", "error")

    except Exception as e:
        conn.rollback()
        flash(f"Error deleting user: {str(e)}", "error")
    finally:
        conn.close()

    return redirect(url_for("admin_routes.admin_users"))


@admin_routes.route("/admin/users/<int:user_id>/toggle-active", methods=["POST"])
@admin_required
def toggle_user_active(user_id):
    """Toggle user active status"""
    conn = get_db_connection()

    try:
        # Get current status
        user = conn.execute(
            "SELECT username, is_active FROM users WHERE id = ?", (user_id,)
        ).fetchone()

        if user:
            new_status = not user["is_active"]
            conn.execute(
                "UPDATE users SET is_active = ? WHERE id = ?", (new_status, user_id)
            )
            conn.commit()

            status_text = "activated" if new_status else "deactivated"
            flash(f'User "{user["username"]}" {status_text} successfully', "success")
        else:
            flash("User not found", "error")

    except Exception as e:
        conn.rollback()
        flash(f"Error updating user: {str(e)}", "error")
    finally:
        conn.close()

    return redirect(url_for("admin_routes.admin_users"))
