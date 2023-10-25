#!/usr/bin/env python3
#
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

from __future__ import annotations
from typing import Union, Optional
from markupsafe import Markup
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    abort,
    send_from_directory,
    make_response,
)
from datetime import datetime
from time import time
from secrets import token_urlsafe
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import sqlite3

app = Flask(__name__)

ucon = sqlite3.connect("udb.db", check_same_thread=False)
scon = sqlite3.connect("sdb.db", check_same_thread=False)
loginclasses = ("students",)

# remember ?con.commit()


def check_login(loginclass: str, username: str, password: str) -> Optional(Bool):
    ucur = ucon.cursor()
    if loginclass not in loginclasses:
        raise ValueError("loginclass", loginclass)
    ucur.execute("SELECT argon2 FROM %s WHERE username = ?" % loginclass, (username,))
    try:
        target = ucur.fetchall()[0][0]
    except IndexError:
        return None
    ucur.close()
    try:
        ph = PasswordHasher()
        ph.verify(target, password)
        return True
    except VerifyMismatchError:
        return False


# print(check_login("teachers", "runxi.yu", "redacted"))


def check_cookie(cookie: Optional(str)) -> Optional(str):
    ucur = ucon.cursor()
    for each in loginclasses:
        ucur.execute(
            "SELECT username, cookietime FROM %s WHERE cookie = ?" % each, (cookie,)
        )
    res = ucur.fetchall()
    if len(res) > 1:
        raise ValueError(
            "database contains multiple entries of the same cookie", cookie
        )
    elif len(res) == 1:
        username, cookietime = res[0]
        if time() - 24 * 60 * 60 < cookietime < time():
            return username
    return None


def record_cookie(loginclass: str, username: str, cookie: str) -> None:
    ucur = ucon.cursor()
    ucur.execute(
        "UPDATE %s SET cookie = ?, cookietime = ? where username = ?" % loginclass,
        (cookie, time(), username),
    )
    if ucur.rowcount == 0:
        raise ValueError("username not found", username)
    elif ucur.rowcount == 1:
        ucon.commit()
        ucur.close()
        return
    else:
        raise ValueError("duplicate usernames", username)


@app.route("/static/<path:path>", methods=["GET"])
def static_(path: str):
    return send_from_directory("static", path)

def get_nametuple(username: str):
    ucur = ucon.cursor()
    ucur.execute(
        "select lastname, firstname, middlename from students where username = ?",
        (username,),
    )
    res = ucur.fetchall()
    assert len(res) == 1
    return res[0]


# TODO process stuff
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        print(dir(request))
        pass # TODO process stuff
    username = check_cookie(request.cookies.get("session-id"))
    if not username:
        return redirect("/login")
    lastname, firstname, middlename = get_nametuple(username)
    ucur = ucon.cursor()
    ucur.execute("SELECT cid FROM mentees WHERE username = ?", (username,))
    for cid in [x[0] for x in ucur.fetchall()]:
        ucur.execute("SELECT subject, primary_mentor, cid, timestring FROM classes WHERE cid = ?", (cid,))
    return render_template(
        "student.html",
        lastname=lastname,
        firstname=firstname,
        middlename=middlename,
        learning_classes=[(course[0], get_nametuple(course[1]), course[2], course[3]) for course in ucur.fetchall()],
    )

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        username = check_cookie(request.cookies.get("session-id"))
        if username:
            return render_template(
                "login.html",
                note=f'Note: You are already logged in as "{username}". Use this form to login as another user.',
            )
        return render_template("login.html")
    elif not ("username" in request.form and "password" in request.form):
        return render_template(
            "login.html",
            note='Error: Your request does not include the required fields "username" and "password".',
        )
    if not check_login("students", request.form["username"], request.form["password"]):
        return render_template("login.html", note="Error: Invalid credentials.")
    username = request.form["username"]
    session_id = token_urlsafe(64)
    record_cookie("students", username, session_id)
    response = make_response(redirect("/"))
    response.set_cookie("session-id", session_id)
    return response


if __name__ == "__main__":
    try:
        app.run(port=8000, debug=True)
    finally:
        pass
        # close database
