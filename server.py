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

PRODUCTION = False
# Non-HTTPS requests will not work if in production mode.

ALTLAW = True

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
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime
from time import time
from secrets import token_urlsafe
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jinja2 import StrictUndefined
import sqlite3
import requests
import logging

logging.basicConfig(level=logging.DEBUG)
# logging.getLogger("werkzeug").setLevel(logging.WARNING)
import ics
import re

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)  # type: ignore
app.jinja_env.undefined = StrictUndefined

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
        "SELECT username, cookietime FROM users WHERE cookie = ?",
        (cookie,),
    ).fetchall()
    if len(res) > 1:
        raise ValueError(
            "database contains multiple entries of the same cookie",
            cookie,
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


def get_yeargroup(username: str) -> Optional[str]:
    res = con.execute(
        "SELECT year FROM users WHERE username = ?",
        (username,),
    ).fetchall()
    if not res:
        raise GeneralFault("checking year group of null username %s" % username)
    assert (type(res[0][0]) is str) or (res[0][0] is None)
    return res[0][0]


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


@app.route("/meeting/<mid>", methods=["GET", "POST"])
def mview(mid: str) -> Union[Response, werkzeugResponse, str]:
    snotes: List[Union[str, Markup]] = []
    if ALTLAW:
        snotes += "Alternate law is enabled for testing and demonstration &ndash; you may see unnecessary information (such as the inclusion of expired meetings) or other abnormal behaviour."
    try:
        username = check_cookie(request.cookies.get("session-id"))
    except AuthenticationFault:
        return redirect("/login")
    lfmu = get_lfmu(username)

    try:
        intmid = int(mid)
    except ValueError:
        raise  # TODO
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
    elif not mentee:
        other_lfmu = None
        role = "squishist"
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


@app.route("/<username>.ics")
def calendar(username: str) -> Response:
    cal = ics.Calendar()

    res = con.execute(
        "SELECT mid, mentor, mentee, time_start, time_end, notes FROM meetings WHERE mentor = ? or mentee = ?",
        (username, username),
    ).fetchall()

    for mid, mentor, mentee, time_start, time_end, notes in res:
        ev = ics.Event()
        if mentor == username:
            if mentee:
                penguin = get_lfmu(mentee)
            else:
                penguin = None
            mode = "You are the mentor."
        elif mentee == username:
            penguin = get_lfmu(mentor)
            mode = "You are the mentee."
        if penguin:
            ev.name = "%s, %s %s" % (penguin[0], penguin[1], penguin[2])
            ev.organizer = ics.Organizer("%s@ykpaoschool.cn" % penguin[3])
        else:
            ev.name = "Mentoring placeholder"
        ev.begin = datetime.fromtimestamp(time_start - 28800).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        ev.end = datetime.fromtimestamp(time_end - 28800).strftime("%Y-%m-%d %H:%M:%S")
        ev.url = "https://powermentor.andrewyu.org/meeting/%s" % mid
        ev.description = mode + "\n" + notes
        cal.events.add(ev)

    response = make_response(cal.serialize())
    response.headers["Content-Disposition"] = (
        "attachment; filename=%s.ics" % username
    )  # BUG: Potential injection?
    return response


def get_subjectname(subjectid: str) -> str:
    try:
        res = con.execute(
            "SELECT subjectname FROM subjects WHERE subjectid = ?", (subjectid,)
        ).fetchone()[0]
    except TypeError:
        return '"' + subjectid + '"'
    assert type(res) is str
    return res


def get_subjectids(username: Optional[str] = None) -> list[str]:
    if not username:
        res = [r[0] for r in con.execute("SELECT subjectid FROM subjects").fetchall()]
    else:
        res = [
            r[0]
            for r in con.execute(
                "SELECT subjectid FROM subject_associations WHERE username = ?",
                (username,),
            ).fetchall()
        ]
    assert type(res) is list
    return res


@app.route("/expertise")
def expertise() -> Union[Response, werkzeugResponse, str]:
    snotes: List[Union[str, Markup]] = []
    if ALTLAW:
        snotes += "Alternate law is enabled for testing and demonstration &ndash; you may see unnecessary information (such as the inclusion of expired meetings) or other abnormal behaviour."
    try:
        username = check_cookie(request.cookies.get("session-id"))
    except AuthenticationFault:
        return redirect("/login")

    lfmu = get_lfmu(username)
    subjectids = get_subjectids()
    subjectids_user = get_subjectids(username)
    subjects = zip(
        subjectids,
        [get_subjectname(subjectid) for subjectid in subjectids],
        [(True if subjectid in subjectids_user else False) for subjectid in subjectids],
    )
    year = get_yeargroup(username)
    if not year:
        year = "None"

    return render_template(
        "expertise.html",
        lfmu=lfmu,
        snotes=snotes,
        subjects=subjects,
        y0checked="checked" if year == "None" else "",
        y9checked="checked" if year == "Y9" else "",
        y10checked="checked" if year == "Y10" else "",
        y11checked="checked" if year == "Y11" else "",
        y12checked="checked" if year == "Y12" else "",
    )


@app.route("/enlist", methods=["GET", "POST"])
def enlist() -> Union[Response, werkzeugResponse, str]:
    snotes: List[Union[str, Markup]] = []
    if ALTLAW:
        snotes += "Alternate law is enabled for testing and demonstration &ndash; you may see unnecessary information (such as the inclusion of expired meetings) or other abnormal behaviour."
    try:
        username = check_cookie(request.cookies.get("session-id"))
    except AuthenticationFault:
        return redirect("/login")
    lfmu = get_lfmu(username)
    subjects = con.execute(
        "SELECT subjects FROM users WHERE username = ?", (username,)
    ).fetchall()[0][0]
    if request.method == "POST":
        # clean this part up a bit when you get to do so. pass unix timestamps around, not weird strings.
        try:
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
            return render_template(
                "enlist.html",
                lfmu=lfmu,
                snotes=snotes,
                mode="fill",
                subjects=subjects,
            )
        except KeyError:
            snotes.append(
                "Your previous submission was rejected because the request did not contain the necessary fields."
            )
            return render_template(
                "enlist.html",
                lfmu=lfmu,
                snotes=snotes,
                mode="fill",
                subjects=subjects,
            )
        if end.timestamp() <= start.timestamp():
            snotes.append(
                "Your previous submission was rejected because the end time is earlier than the start time."
            )
            return render_template(
                "enlist.html",
                lfmu=lfmu,
                snotes=snotes,
                mode="fill",
                subjects=subjects,
            )
        if end.timestamp() <= time():
            snotes.append(
                "Your previous submission was rejected because the end time is earlier than the current time."
            )
            return render_template(
                "enlist.html",
                lfmu=lfmu,
                snotes=snotes,
                mode="fill",
                subjects=subjects,
            )
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
                subjects=subjects,
            )
        elif request.form["mode"] == "confirmed":
            tstart = int(start.timestamp())
            tend = int(end.timestamp())
            notes = request.form["notes"]
            assert (
                con.execute(
                    "INSERT INTO meetings (mentor, time_start, time_end, notes) VALUES (?, ?, ?, ?)",
                    (username, tstart, tend, notes),
                ).rowcount
                == 1
            )
            con.commit()
            return render_template(
                "enlist.html",
                lfmu=lfmu,
                snotes=snotes,
                mode="confirmed",
                starts=start.strftime("%c"),
                ends=end.strftime("%c"),
                notes=notes,
                subjects=subjects,
            )
        else:
            snotes.append(
                "Why was this even in a POST request? I'm letting you go this time..."
            )
            return render_template(
                "enlist.html",
                lfmu=lfmu,
                snotes=snotes,
                mode="fill",
                subjects=subjects,
            )
    elif request.method == "GET":
        return render_template(
            "enlist.html",
            lfmu=lfmu,
            snotes=snotes,
            mode="fill",
            subjects=subjects,
        )
    else:
        raise GeneralFault()


@app.route("/register", methods=["GET", "POST"])
def register() -> Union[str, Response, werkzeugResponse]:
    snotes: List[Union[str, Markup]] = []
    if ALTLAW:
        snotes += "Alternate law is enabled for testing and demonstration &ndash; you may see unnecessary information (such as the inclusion of expired meetings) or other abnormal behaviour."
    try:
        username = check_cookie(request.cookies.get("session-id"))
    except AuthenticationFault:
        return redirect("/login")
    if request.method == "POST":
        return "this is not british politics"
    lfmu = get_lfmu(username)

    available_meetings = [
        (
            i[0],
            get_lfmu(i[1]),
            [get_subjectname(sid) for sid in get_subjectids(i[1])],
            datetime.fromtimestamp(i[2]).strftime("%c"),
            datetime.fromtimestamp(i[3]).strftime("%c"),
            i[4],
            get_yeargroup(i[1]),
        )
        if ALTLAW:
            for i in con.execute(
                "SELECT mid, mentor, time_start, time_end, notes FROM meetings WHERE mentor != ? AND coalesce(mentee, '') = ''",
                (username,),
            ).fetchall()
        else:
            for i in con.execute(
                "SELECT mid, mentor, time_start, time_end, notes FROM meetings WHERE mentor != ? AND coalesce(mentee, '') = '' AND time_end > ?",
                (username, time()),
            ).fetchall()
    ]

    # TODO
    return render_template(
        "register.html",
        lfmu=lfmu,
        available_meetings=available_meetings,
        snotes=snotes,
    )


@app.route("/", methods=["GET", "POST"])
def index() -> Union[str, Response, werkzeugResponse]:
    snotes: List[Union[str, Markup]] = []
    if ALTLAW:
        snotes += "Alternate law is enabled for testing and demonstration &ndash; you may see unnecessary information (such as the inclusion of expired meetings) or other abnormal behaviour."
    try:
        username = check_cookie(request.cookies.get("session-id"))
    except AuthenticationFault:
        return redirect("/login")
    if request.method == "POST":
        try:
            if request.form["action"] == "deregister_meeting":
                res = con.execute(
                    "SELECT mentor, mentee FROM meetings WHERE mid = ?",
                    (request.form["mid"],),
                ).fetchall()
                if len(res) != 1:
                    snotes.append(
                        "You tried to deregister from meeting %s but it doesn't even exist or you don't have permissions"
                        % request.form["mid"]
                    )
                else:
                    mentor, mentee = res[0]
                    if username == mentor:
                        assert (
                            con.execute(
                                "DELETE FROM meetings WHERE mid = ?",
                                (request.form["mid"],),
                            ).rowcount
                            == 1
                        )
                        con.commit()
                        snotes.append(
                            "You have deregistered from, and deleted, meeting %s"
                            % request.form["mid"]
                        )
                        # somehow notify mentee with request.form["reason"]
                    elif username == mentee:
                        assert (
                            con.execute(
                                "UPDATE meetings SET mentee = NULL WHERE mid = ?",
                                (request.form["mid"],),
                            ).rowcount
                            == 1
                        )
                        con.commit()
                        snotes.append(
                            "You have deregistered from meeting %s"
                            % request.form["mid"]
                        )
                        # somehow notify mentor with request.form["reason"]
                    else:
                        snotes.append(
                            "You tried to deregister from meeting %s but it doesn't even exist or you don't have permissions"
                            % request.form["mid"]
                        )
            elif request.form["action"] == "expertise":
                con.execute(
                    "DELETE FROM subject_associations WHERE username = ?",
                    (username,),
                )
                records = [(username, i) for i in request.form.getlist("expertise")]
                con.executemany(
                    "INSERT INTO subject_associations VALUES(?, ?)", records
                )
                year = request.form.get("year", "None")
                if year in ["None", "Y9", "Y10", "Y11", "Y12"]:
                    con.execute(
                        "UPDATE users SET year = ? WHERE USERNAME = ?",
                        (year, username),
                    )
                    explode = False
                else:
                    explode = True
                if explode:
                    con.rollback()
                    snotes.append(
                        "That's not a valid year group, you might want to try again."
                    )
                else:
                    con.commit()  # Not really
                    snotes.append(
                        "You just submitted your subject expertise and year group"
                    )
            elif request.form["action"] == "register_meeting":
                res = con.execute(
                    "SELECT mentor, mentee FROM meetings WHERE mid = ?",
                    (request.form["mid"],),
                ).fetchall()
                if len(res) != 1 or res[0][1]:
                    snotes.append(
                        "The meeting you were trying to register disappeared, perhaps someone registered it just now, or the mentor deleted it?"
                    )
                elif username == res[0][0]:
                    snotes.append("NEIN DANKE")
                else:
                    assert (
                        con.execute(
                            "UPDATE meetings SET mentee = ? WHERE mid = ?",
                            (
                                username,
                                request.form["mid"],
                            ),
                        ).rowcount
                        == 1
                    )
                    con.commit()
                    snotes.append(
                        "You have registered for meeting %s" % request.form["mid"]
                    )
                    # somehow notify mentor
            else:
                return "this is not american politics"
        except KeyError:
            raise
        pass  # TODO process stuff
    lfmu = get_lfmu(username)

    meetings_as_mentee = [
        (
            i[0],
            get_lfmu(i[1]),
            datetime.fromtimestamp(i[2]).strftime("%c"),
        )
        for i in con.execute(
            "SELECT mid, mentor, time_start FROM meetings WHERE mentee = ?",
            (username,),
        ).fetchall()
    ]

    meetings_as_mentor = [
        (
            i[0],
            get_lfmu(i[1]) if i[1] else null_lfmu,
            datetime.fromtimestamp(i[2]).strftime("%c"),
        )
        for i in con.execute(
            "SELECT mid, mentee, time_start FROM meetings WHERE mentor = ?",
            (username,),
        ).fetchall()
    ]

    # TODO
    return render_template(
        "index.html",
        lfmu=lfmu,
        meetings_as_mentee=meetings_as_mentee,
        meetings_as_mentor=meetings_as_mentor,
        subjects=[get_subjectname(sid) for sid in get_subjectids(username)],
        snotes=snotes,
        username=username,
    )


def check_powerschool(username: str, password: str) -> tuple[str, str, str]:
    ss = requests.Session()

    rq = ss.post(
        "https://powerschool.ykpaoschool.cn/guardian/home.html",
        data={
            "request_locale": "en_US",
            "account": username,
            "pw": password,
            "ldappassword": password,
        },
    )

    html = ss.get("https://powerschool.ykpaoschool.cn/guardian/home.html").text

    match = re.search(
        r"<h1>Grades and Attendance: ([A-Za-z]+), ([A-Za-z]+) (.*)</h1>",
        html,
    )

    if not match:
        raise AuthenticationFault

    return match.group(1), match.group(2), match.group(3)


@app.route("/login", methods=["GET", "POST"])
def login() -> Union[Response, werkzeugResponse, str]:
    if request.method == "GET":
        logging.debug("GET on /login")
        try:
            logging.debug("session-id %s" % request.cookies.get("session-id") or "none")
            username = check_cookie(request.cookies.get("session-id"))
            logging.debug("username yes %s" % username)
        except AuthenticationFault:
            # this is normal as they're probably first retreiving /login with GET
            return render_template("login.html", note="")
        else:
            return render_template(
                "login.html",
                note=f'Note: You are already logged in as "{username}". Use this form to login as another user.',
            )
    logging.debug("POST on /login")
    if not (
        "mode" in request.form
        and "username" in request.form
        and "password" in request.form
    ):
        return "you should squish more penguins"
    if request.form["mode"] == "login":
        logging.debug("Mode login")
        try:
            logging.debug(
                "checking login %s %s"
                % (request.form["username"], request.form["password"])
            )
            check_login(request.form["username"], request.form["password"])
            logging.debug("success")
            # should continue to cookie-setter
        except AuthenticationFault:
            logging.debug("fail")
            return render_template("login.html", note="Error: Invalid credentials.")
        username = request.form["username"]
    elif request.form["mode"] == "psauth":
        logging.debug("Mode psauth")
        try:
            lastname, firstname, middlename = check_powerschool(
                request.form["username"], request.form["password"]
            )
        except AuthenticationFault:
            return render_template(
                "login.html",
                note="Error: Invalid PowerSchool credentials (or maybe you just have an unusual name that my regular expression fails to parse).",
            )
        username = request.form["username"]
        password = request.form["password"]
        lf = len(
            con.execute(
                "SELECT username FROM users WHERE username = ?",
                (username,),
            ).fetchall()
        )
        if lf > 1:
            raise DatabaseFault(username)
        elif lf == 1:
            assert (
                con.execute(
                    "UPDATE users SET argon2 = ?, lastname = ?, firstname = ?, middlename = ? WHERE username = ?",
                    (
                        PasswordHasher().hash(password),
                        lastname,
                        firstname,
                        middlename,
                        username,
                    ),
                ).rowcount
                == 1
            )
            con.commit()
        elif lf == 0:
            assert (
                con.execute(
                    "INSERT INTO users (username, argon2, lastname, firstname, middlename) VALUES (?, ?, ?, ?, ?)",
                    (
                        username,
                        PasswordHasher().hash(password),
                        lastname,
                        firstname,
                        middlename,
                    ),
                ).rowcount
                == 1
            )
            con.commit()
    else:
        return "donald trump ate my pufferfish!!1"

    session_id = token_urlsafe(16)
    logging.debug("setting session-id %s" % session_id)
    record_cookie(username, session_id)
    logging.debug("recorded cookie... supposedly")
    response = make_response(redirect("/"))
    response.set_cookie("session-id", session_id, secure=PRODUCTION, httponly=True)
    logging.debug("set cookie... supposedly")
    return response


@app.route("/impersonate", methods=["GET", "POST"])
def impersonate() -> Union[Response, werkzeugResponse, str, tuple[str, int]]:
    if not (
        request.remote_addr == "127.0.0.1"
        or check_cookie(request.cookies.get("session-id")) == "s22537"
    ):
        return "You may not access this resource.", 403
    if request.method == "GET":
        return render_template(
            "impersonate.html",
            users=[
                (username, lastname + ", " + firstname + " " + middlename)
                for (username, lastname, firstname, middlename) in con.execute(
                    "SELECT username, lastname, firstname, middlename FROM users"
                ).fetchall()
            ],
        )
    # From now on it's POST
    if not ("username" in request.form):
        return "you cant impersonate god"
    username = request.form["username"]
    session_id = token_urlsafe(16)
    logging.debug("setting session-id %s" % session_id)
    record_cookie(username, session_id)
    logging.debug("recorded cookie... supposedly")
    response = make_response(redirect("/"))
    response.set_cookie("session-id", session_id, secure=PRODUCTION, httponly=True)
    logging.debug("set cookie... supposedly")
    return response


if __name__ == "__main__":
    try:
        app.run(port=48139, debug=(not PRODUCTION), use_reloader=(not PRODUCTION))
    finally:
        con.commit()
        con.close()
        pass
