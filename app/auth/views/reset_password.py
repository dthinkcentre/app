from flask import request, flash, render_template, redirect, url_for
from flask_login import login_user
from flask_wtf import FlaskForm
from wtforms import StringField, validators

from app.auth.base import auth_bp
from app.extensions import db
from app.models import ResetPasswordCode


class ResetPasswordForm(FlaskForm):
    password = StringField(
        "Password", validators=[validators.DataRequired(), validators.Length(min=8)]
    )


@auth_bp.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    form = ResetPasswordForm(request.form)

    reset_password_code_str = request.args.get("code")

    reset_password_code: ResetPasswordCode = ResetPasswordCode.get_by(
        code=reset_password_code_str
    )

    if not reset_password_code:
        error = (
            "The reset password link can be used only once. "
            "Please request a new link to reset password."
        )
        return render_template("auth/reset_password.html", form=form, error=error)

    if reset_password_code.is_expired():
        error = "The link has been already expired. Please make a new request of the reset password link"
        return render_template("auth/reset_password.html", form=form, error=error)

    if form.validate_on_submit():
        user = reset_password_code.user

        user.set_password(form.password.data)

        flash("Your new password has been set", "success")

        # this can be served to activate user too
        user.activated = True

        # remove the reset password code
        ResetPasswordCode.delete(reset_password_code.id)

        db.session.commit()
        login_user(user)

        return redirect(url_for("dashboard.index"))

    return render_template("auth/reset_password.html", form=form)
