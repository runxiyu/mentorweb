#!/usr/bin/env python

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
# BUGS
# Time-based side-channel attacks are possible.
#
# TODOS
# Test for time overlaps.
# Redirect to login page, but allow coming back somehow? Perhaps a Referrer header.

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
null_lfmu = ("None", "None", "(None)", "none")


class GeneralFault(Exception):
    pass


class AuthenticationFault(GeneralFault):
    pass


class DatabaseFault(GeneralFault):
    pass


def check_login(username: str, password: str) -> None:
    try:
        target = con.execute(
            "SELECT argon2 FROM users WHERE username = ?", (username,)
        ).fetchall()[0][0]
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
        raise ValueError(
            "database contains multiple entries of the same cookie", cookie
        )
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
                snotes.append("You have successfully registered in this section.")
            else:
                return "stop haxing the requests thanks"
        except KeyError:
            raise
        pass
"""


@app.route("/meeting/<mid>", methods=["GET", "POST"])
def mview(mid: str) -> Union[Response, werkzeugResponse, str]:
    snotes: List[Union[str, Markup]] = []
    try:
        username = check_cookie(request.cookies.get("session-id"))
    except AuthenticationFault:
        return redirect("/login")
    lfmu = get_lfmu(username)

    try:
        intmid = int(mid)
    except ValueError:
        raise # TODO
    res = con.execute(
        "SELECT mentor, mentee, time_start, time_end, notes FROM meetings WHERE mid = ?",
        (intmid,),
    ).fetchall()
    assert len(res) <= 1
    if len(res) == 0:  # meeting does not exist
        return render_template("meeting.html", role="bad", snotes=snotes, lfmu=lfmu)
    mentor, mentee, time_start, time_end, notes = res[0]
    if username == mentor:
        role = "mentor"
        other_lfmu = get_lfmu(mentee) if mentee else null_lfmu
    elif username == mentee:
        role = "mentee"
        other_lfmu = get_lfmu(mentor)
    else:  # user is not related to the meeting
        return render_template(
            "meeting.html",
            role="bad",
            lfmu=lfmu,
            snotes=snotes,
        )
    return render_template(
        "meeting.html",
        role=role,
        lfmu=lfmu,
        mid=mid,
        other_lfmu=other_lfmu,
        time_start=datetime.fromtimestamp(time_start).strftime("%c"),
        time_end=datetime.fromtimestamp(time_end).strftime("%c"),
        notes=notes,
        snotes=snotes,
    )


@app.route("/calendar/<username>.ics")
def calendar(username: str) -> Response:
    ical = ""
    # TODO: Actually generate a calendar
    response = make_response(ical)
    response.headers["Content-Disposition"] = "attachment; filename=calendar.ics"
    return response


@app.route("/expertise")
def expertise() -> Union[Response, werkzeugResponse, str]:
    snotes: List[Union[str, Markup]] = []
    try:
        username = check_cookie(request.cookies.get("session-id"))
    except AuthenticationFault:
        return redirect("/login")
    lfmu = get_lfmu(username)
    return Response()


@app.route("/enlist", methods=["GET", "POST"])
def enlist() -> Union[Response, werkzeugResponse, str]:
    snotes: List[Union[str, Markup]] = []
    try:
        username = check_cookie(request.cookies.get("session-id"))
    except AuthenticationFault:
        return redirect("/login")
    lfmu = get_lfmu(username)
    if request.method == "POST":
        # clean this part up a bit when you get to do so. pass unix timestamps around, not weird strings.
        try:
            print(request.form)
            if "date" not in request.form:
                date = ""
            else:
                date = request.form["date"] + " "
            start = datetime.strptime(date + request.form["start"], "%Y-%m-%d %H:%M")
            end = datetime.strptime(date + request.form["end"], "%Y-%m-%d %H:%M")
        except ValueError:
            snotes.append(
                "Your previous submission was rejected because the date or time formats were unreadable."
            )
            return render_template("enlist.html", lfmu=lfmu, snotes=snotes, mode="fill")
        except KeyError:
            snotes.append(
                "Your previous submission was rejected because the request did not contain the necessary fields."
            )
            return render_template("enlist.html", lfmu=lfmu, snotes=snotes, mode="fill")
        if end.timestamp() <= start.timestamp():
            snotes.append(
                "Your previous submission was rejected because the end time is earlier than the start time. Butter fingers! I still don't want to use JavaScript, sue me."
            )
            return render_template("enlist.html", lfmu=lfmu, snotes=snotes, mode="fill")
        if request.form["mode"] == "confirm":
            return render_template(
                "enlist.html",
                lfmu=lfmu,
                snotes=snotes,
                mode="confirm",
                start=start.strftime("%Y-%m-%d %H:%M"),
                end=end.strftime("%Y-%m-%d %H:%M"),
                starts=start.strftime("%c"),
                ends=end.strftime("%c"),
                notes=request.form["notes"],
            )
        elif request.form["mode"] == "confirmed":
            tstart = int(start.timestamp())
            tend = int(end.timestamp())
            notes = request.form["notes"]
            assert con.execute("INSERT INTO meetings (mentor, time_start, time_end, notes) VALUES (?, ?, ?, ?)", (username, tstart, tend, notes)).rowcount == 1
            con.commit()
            return render_template(
                "enlist.html",
                lfmu=lfmu,
                snotes=snotes,
                mode="confirmed",
                starts=start.strftime("%c"),
                ends=end.strftime("%c"),
                notes=notes
            )
        else:
            snotes.append(
                "Why was this even in a POST request? I'm letting you go this time..."
            )
            return render_template("enlist.html", lfmu=lfmu, snotes=snotes, mode="fill")
    elif request.method == "GET":
        return render_template("enlist.html", lfmu=lfmu, snotes=snotes, mode="fill")
    else:
        raise GeneralFault()


@app.route("/", methods=["GET", "POST"])
def index() -> Union[str, Response, werkzeugResponse]:
    snotes = []
    try:
        username = check_cookie(request.cookies.get("session-id"))
    except AuthenticationFault:
        return redirect("/login")
    if request.method == "POST":
        try:
            if request.form["action"] == "deregister_meeting":
                res = con.execute("SELECT mentor, mentee FROM meetings WHERE mid = ?", (request.form["mid"])).fetchall()
                if len(res) != 1:
                    snotes.append("You tried to deregister from meeting %s but it doesn't even exist or you don't have permissions" % request.form["mid"])
                else:
                    mentor, mentee = res[0]
                    if username == mentor:
                        assert con.execute("DELETE FROM meetings WHERE mid = ?", (request.form["mid"],),).rowcount == 1
                        con.commit()
                        snotes.append(
                            "You have deregistered from, and deleted, meeting %s" % request.form["mid"]
                        )
                        # somehow notify mentee with request.form["reason"]
                    elif username == mentee:
                        assert con.execute("UPDATE meetings SET mentee = \"\" WHERE mid = ?", (request.form["mid"],),).rowcount == 1
                        con.commit()
                        snotes.append(
                            "You have deregistered from meeting %s" % request.form["mid"]
                        )
                        # somehow notify mentor with request.form["reason"]
                    else:
                        snotes.append("You tried to deregister from meeting %s but it doesn't even exist or you don't have permissions" % request.form["mid"])
            else:
                return "stop haxing the requests thanks"
        except KeyError:
            raise
        pass  # TODO process stuff
    lfmu = get_lfmu(username)

    meetings_as_mentee = [(i[0], get_lfmu(i[1]), datetime.fromtimestamp(i[2]).strftime("%c")) for i in con.execute("SELECT mid, mentor, time_start FROM meetings WHERE mentee = ?", (username,)).fetchall()]

    meetings_as_mentor = [(i[0], get_lfmu(i[1]) if i[1] else null_lfmu, datetime.fromtimestamp(i[2]).strftime("%c")) for i in con.execute("SELECT mid, mentee, time_start FROM meetings WHERE mentor = ?", (username,)).fetchall()]


    # TODO
    return render_template(
        "index.html",
        lfmu=lfmu,
        meetings_as_mentee=meetings_as_mentee,
        meetings_as_mentor=meetings_as_mentor,
        snotes=snotes,
    )




@app.route("/login", methods=["GET", "POST"])
def login() -> Union[Response, werkzeugResponse, str]:
    if request.method == "GET":
        try:
            username = check_cookie(request.cookies.get("session-id"))
        except AuthenticationFault:
            return render_template("login.html")
        else:
            return render_template(
                "login.html",
                note=f'Note: You are already logged in as "{username}". Use this form to login as another user.',
            )
    elif not ("username" in request.form and "password" in request.form):
        return render_template(
            "login.html",
            note='Error: Your request does not include the required fields "username" and "password".',
        )
    try:
        check_login(request.form["username"], request.form["password"])
    except AuthenticationFault:
        return render_template("login.html", note="Error: Invalid credentials.")
    username = request.form["username"]
    session_id = token_urlsafe(16)
    record_cookie(username, session_id)
    response = make_response(redirect("/"))
    response.set_cookie("session-id", session_id)
    return response


if __name__ == "__main__":
    try:
        app.run(port=8000, debug=True)
    finally:
        pass
    # close database
