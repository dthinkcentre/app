from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app.config import EMAIL_SERVERS_WITH_PRIORITY, DKIM_DNS_VALUE, EMAIL_DOMAIN
from app.dashboard.base import dashboard_bp
from app.dns_utils import (
    get_mx_domains,
    get_spf_domain,
    get_dkim_record,
    get_txt_record,
)
from app.extensions import db
from app.models import CustomDomain, Alias


@dashboard_bp.route("/domains/<int:custom_domain_id>/dns", methods=["GET", "POST"])
@login_required
def domain_detail_dns(custom_domain_id):
    custom_domain = CustomDomain.get(custom_domain_id)
    if not custom_domain or custom_domain.user_id != current_user.id:
        flash("You cannot see this page", "warning")
        return redirect(url_for("dashboard.index"))

    mx_ok = spf_ok = dkim_ok = True
    mx_errors = spf_errors = dkim_errors = []

    if request.method == "POST":
        if request.form.get("form-name") == "check-mx":
            mx_domains = get_mx_domains(custom_domain.domain)

            if sorted(mx_domains) != sorted(EMAIL_SERVERS_WITH_PRIORITY):
                flash("The MX record is not correctly set", "warning")
                mx_ok = False
                # build mx_errors to show to user
                mx_errors = [
                    f"{priority} {domain}" for (priority, domain) in mx_domains
                ]
            else:
                flash(
                    "Your domain is verified. Now it can be used to create custom alias",
                    "success",
                )
                custom_domain.verified = True
                db.session.commit()
                return redirect(
                    url_for(
                        "dashboard.domain_detail_dns", custom_domain_id=custom_domain.id
                    )
                )
        elif request.form.get("form-name") == "check-spf":
            spf_domains = get_spf_domain(custom_domain.domain)
            if EMAIL_DOMAIN in spf_domains:
                custom_domain.spf_verified = True
                db.session.commit()
                flash("The SPF is setup correctly", "success")
                return redirect(
                    url_for(
                        "dashboard.domain_detail_dns", custom_domain_id=custom_domain.id
                    )
                )
            else:
                flash(
                    f"SPF: {EMAIL_DOMAIN} is not included in your SPF record.",
                    "warning",
                )
                spf_ok = False
                spf_errors = get_txt_record(custom_domain.domain)

        elif request.form.get("form-name") == "check-dkim":
            dkim_record = get_dkim_record(custom_domain.domain)
            correct_dkim_record = f"v=DKIM1; k=rsa; p={DKIM_DNS_VALUE}"
            if dkim_record == correct_dkim_record:
                flash("The DKIM is setup correctly.", "success")
                custom_domain.dkim_verified = True
                db.session.commit()

                return redirect(
                    url_for(
                        "dashboard.domain_detail_dns", custom_domain_id=custom_domain.id
                    )
                )
            else:
                flash("DKIM: the TXT record is not correctly set", "warning")
                dkim_ok = False
                dkim_errors = get_txt_record(f"dkim._domainkey.{custom_domain.domain}")

    spf_record = f"v=spf1 include:{EMAIL_DOMAIN} -all"

    dkim_record = f"v=DKIM1; k=rsa; p={DKIM_DNS_VALUE}"

    return render_template(
        "dashboard/domain_detail/dns.html",
        EMAIL_SERVERS_WITH_PRIORITY=EMAIL_SERVERS_WITH_PRIORITY,
        **locals(),
    )


@dashboard_bp.route("/domains/<int:custom_domain_id>/info", methods=["GET", "POST"])
@login_required
def domain_detail(custom_domain_id):
    custom_domain = CustomDomain.get(custom_domain_id)
    if not custom_domain or custom_domain.user_id != current_user.id:
        flash("You cannot see this page", "warning")
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        if request.form.get("form-name") == "switch-catch-all":
            custom_domain.catch_all = not custom_domain.catch_all
            db.session.commit()

            if custom_domain.catch_all:
                flash(
                    f"The catch-all has been enabled for {custom_domain.domain}",
                    "success",
                )
            else:
                flash(
                    f"The catch-all has been disabled for {custom_domain.domain}",
                    "warning",
                )
            return redirect(
                url_for("dashboard.domain_detail", custom_domain_id=custom_domain.id)
            )
        elif request.form.get("form-name") == "delete":
            name = custom_domain.domain
            CustomDomain.delete(custom_domain_id)
            db.session.commit()
            flash(f"Domain {name} has been deleted", "success")

            return redirect(url_for("dashboard.custom_domain"))

    nb_alias = Alias.filter_by(custom_domain_id=custom_domain.id).count()

    return render_template("dashboard/domain_detail/info.html", **locals())
