#!/usr/bin/env python3

# Copyright (C) 2023  Runxi Yu <a@andrewyu.org>
# Blue passes for YK Pao School
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# Time-based side-channel attacks are possible.

from __future__ import annotations
from typing import Union, Optional, Tuple, List
from markupsafe import Markup
from flask import (
    Flask,
    Response,
    render_template,
    request,
    redirect,
    abort,
    send_from_directory,
    make_response,
)
from werkzeug.wrappers.response import Response as werkzeugResponse
from datetime import datetime
from time import time
from secrets import token_urlsafe
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import sqlite3

app = Flask(__name__)

con = sqlite3.connect("yay.db", check_same_thread=False)


class GeneralFault(Exception):
    pass


class AuthenticationFault(GeneralFault):
    pass


class DatabaseFault(GeneralFault):
    pass


def check_login(username: str, password: str) -> None:
    try:
        target = con.execute("SELECT argon2 FROM users WHERE username = ?", (username,)).fetchall()[
            0
        ][0]
        assert type(target) is str
    except IndexError:
        raise AuthenticationFault("username", username)
    try:
        ph = PasswordHasher()
        ph.verify(target, password)
        return
    except VerifyMismatchError:
        raise AuthenticationFault("username", username)


def check_cookie(cookie: Optional[str]) -> str:
    if not cookie:
        raise AuthenticationFault("cookie", cookie)
    res = con.execute(
        "SELECT username, cookietime FROM users WHERE cookie = ?", (cookie,)
    ).fetchall()
    if len(res) > 1:
        raise ValueError("database contains multiple entries of the same cookie", cookie)
    elif len(res) == 1:
        username, cookietime = res[0]
        assert type(username) is str
        assert type(cookietime) is float
        if time() - 24 * 60 * 60 < cookietime < time():
            return username
    raise AuthenticationFault("cookie", cookie)


def record_cookie(username: str, cookie: str) -> None:
    rowcount = con.execute(
        "UPDATE users SET cookie = ?, cookietime = ? WHERE username = ?",
        (cookie, time(), username),
    ).rowcount
    assert rowcount < 2
    if rowcount == 0:
        raise ValueError(username)
    elif rowcount == 1:
        con.commit()
        return


@app.route("/static/<path:path>", methods=["GET"])
def static_(path: str) -> Response:
    return send_from_directory("static", path)


def get_lfmu(username: str) -> Tuple[str, str, str, str]:
    res = con.execute(
        "SELECT lastname, firstname, middlename FROM users WHERE username = ?",
        (username,),
    ).fetchall()
    assert len(res) == 1
    assert (
        type(res[0]) is tuple
        and type(res[0][0]) is str
        and type(res[0][1]) is str
        and type(res[0][2]) is str
    )
    return (res[0][0], res[0][1], res[0][2], username)


"""
    if request.method == "POST":
        try:
            if request.form["action"] == "register":
                # TODO: Check if the course exists first, to avoid cluttering the database
                cur.execute("INSERT INTO mentees VALUES (?, ?)", (username, cid))
                sysmsgs.append("You have successfully registered in this section.")
            else:
                return "stop haxing the requests thanks"
        except KeyError:
            raise
        pass
"""


@app.route("/meeting/<mid>", methods=["GET", "POST"])
def mview(mid: str) -> Union[Response, werkzeugResponse, str]:
    sysmsgs: List[Union[str, Markup]] = []
    try:
        username = check_cookie(request.cookies.get("session-id"))
    except AuthenticationFault:
        return redirect("/login")
    nametuple = get_lfmu(username)

    res = con.execute(
        "SELECT mid, subject, mentor, mentee, time_start, time_end, description FROM meetings WHERE mid = ?",
        (mid,),
    ).fetchall()
    assert len(res) <= 1
    if len(res) == 0:  # meeting does not exist
        return render_template("meeting.html", role="bad", sysmsgs=sysmsgs)
    cid, subject, mentor, mentee, time_start, time_end, description = res[0]
    if username == mentor:
        return render_template(
            "meeting.html",
            role="mentor",
            sysmsgs=sysmsgs,
        )
    elif username == mentee:
        return render_template(
            "meeting.html",
            role="mentee",
            sysmsgs=sysmsgs,
        )
    else:  # user is not related to the meeting
        return render_template(
            "meeting.html",
            role="bad",
            sysmsgs=sysmsgs,
        )
    # TODO


#     cur.execute("SELECT username FROM mentees WHERE cid = ?", (cid,))
#     mentees = [x[0] for x in cur.fetchall()]
#     return render_template(
#         "meeting.html",
#         role="mentee",
#         nametuple=nametuple,
#         subject=subject,
#         primary_mentor=get_nametuple(primary_mentor) + tuple([primary_mentor]),
#         mentees=[(get_nametuple(mentee) + tuple([mentee])) for mentee in mentees],
#         cid=cid,
#         timestring=timestring,
#         description=description,
#         sysmsgs=sysmsgs,
#     )


#
# @app.route("/calendar/<username>.ics")
# def calendar(username: str):
#     ical = ""
#     # TODO: Actually generate a calendar
#     response = make_response(ical)
#     response.headers["Content-Disposition"] = "attachment; filename=calendar.ics"
#     return response
#
#
# @app.route("/", methods=["GET", "POST"])
# def index():
#     sysmsgs = []
#     cur = con.cursor()
#     username = check_cookie(request.cookies.get("session-id"))
#     if not username:
#         return redirect("/login")
#     if request.method == "POST":
#         try:
#             if request.form["action"] == "deregister":
#                 cur.execute(
#                     "DELETE FROM mentees WHERE username = ? AND cid = ?",
#                     (
#                         username,
#                         request.form["classid"],
#                     ),
#                 )
#                 if not cur.rowcount:
#                     sysmsgs.append(
#                         "Deregister failed: You are not registered in section %s"
#                         % request.form["classid"]
#                     )
#                 else:
#                     sysmsgs.append(
#                         "You have deregistered from section %s" % request.form["classid"]
#                     )
#             else:
#                 return "stop haxing the requests thanks"
#         except KeyError:
#             raise
#         pass  # TODO process stuff
#     nametuple = get_nametuple(username)
#
#     cur.execute("SELECT cid FROM mentees WHERE username = ?", (username,))
#     for cid in [x[0] for x in cur.fetchall()]:
#         cur.execute(
#             "SELECT subject, primary_mentor, cid, timestring FROM classes WHERE cid = ?",
#             (cid,),
#         )
#     learning_classes = [
#         (course[0], get_nametuple(course[1]), course[2], course[3]) for course in cur.fetchall()
#     ]
#
#     cur.execute("SELECT cid FROM mentees WHERE username = ?", (username,))
#     for cid in [x[0] for x in cur.fetchall()]:
#         cur.execute(
#             "SELECT subject, primary_mentor, cid, timestring FROM classes WHERE cid = ?",
#             (cid,),
#         )
#     available_classes = []
#
#     # TODO
#     return render_template(
#         "student.html",
#         nametuple=nametuple,
#         learning_meetings=learning_classes,
#         available_classes=available_classes,
#         sysmsgs=sysmsgs,
#     )
#
#
# @app.route("/login", methods=["GET", "POST"])
# def login():
#     if request.method == "GET":
#         username = check_cookie(request.cookies.get("session-id"))
#         if username:
#             return render_template(
#                 "login.html",
#                 note=f'Note: You are already logged in as "{username}". Use this form to login as another user.',
#             )
#         return render_template("login.html")
#     elif not ("username" in request.form and "password" in request.form):
#         return render_template(
#             "login.html",
#             note='Error: Your request does not include the required fields "username" and "password".',
#         )
#     if not check_login("students", request.form["username"], request.form["password"]): # TODO check_login error
#         return render_template("login.html", note="Error: Invalid credentials.")
#     username = request.form["username"]
#     session_id = token_urlsafe(64)
#     record_cookie("students", username, session_id)
#     response = make_response(redirect("/"))
#     response.set_cookie("session-id", session_id)
#     return response


if __name__ == "__main__":
    try:
        app.run(port=8000, debug=True)
    finally:
        pass
        # close database
