#!/usr/bin/env python3
#
# Copyright (C) 2023  Runxi Yu <a@andrewyu.org>
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
from hashlib import sha512
from secrets import token_urlsafe
import json
import sqlite3


app = Flask(__name__)
conn = sqlite3.connect("database.db")
cur = conn.cursor()


global userdb
global classdb


def read_cdb() -> None:
    cdb = []
    try:
        sql_search = "SELECT * FROM cdb"
        cur.execute(sql_search)
        results = cur.fetchall()
        for result in results: 
            cdb.append({"cid": str(result[0])})
            json_content = json.loads(result[1].replace("'", '"'))
            cdb[-1].update(json_content)
    except BaseException as e: 
        print(e)
    return cdb


def write_cdb() -> None:
    try:
        cur.execute("DELETE FROM cdb")
        for entry in classdb: 
            cid = int(entry.pop("cid"))
            sql_insert = "INSERT INTO cdb VALUES(" + str(cid) + ', "' + str(entry) + '")'
            cur.execute(sql_insert)
        conn.commit()
    except BaseException as e: 
        print(e)


def read_udb() -> None:
    udb = []
    try:
        sql_search = "SELECT * FROM udb"
        cur.execute(sql_search)
        results = cur.fetchall()
        for result in results: 
            udb.append({"username": "s" + str(result[0])})
            json_content = json.loads(result[1].replace("'", '"'))
            udb[-1].update(json_content)
    except BaseException as e: 
        print(e)
    return udb


def write_udb() -> None:
    try:
        cur.execute("DELETE FROM udb")
        for entry in userdb: 
            username = int(entry.pop("username")[1:])
            sql_insert = "INSERT INTO udb VALUES(" + str(username) + ', "' + str(entry) + '")'
            cur.execute(sql_insert)
        conn.commit()
    except BaseException as e: 
        print(e)


userdb = read_udb()
classdb = read_cdb()


def check_login(username: str, password: str) -> Optional(str):
    for udic in userdb:
        if udic["username"] == username:
            try:
                salted = (udic["salt"] + ":" + password).encode("utf-8")
            except UnicodeEncodeError:
                return None
            if sha512(salted).hexdigest() == udic["password"]:
                return True
            else:
                return None
    return None


# /


def check_cookie(cookie: Optional(str)) -> Optional(str):
    for udic in userdb:
        if cookie in udic["cookies"]:
            return udic["username"]
    return False


def add_cookie(username: str, cookie: str) -> None:
    for udic in userdb:
        if username == udic["username"]:
            udic["cookies"].append(cookie)
            return None
    raise ValueError(f'User "{username}" not found')


def get_udic(username: Optional(str)):
    for udic in userdb:
        if username == udic["username"]:
            return udic

def get_cdic(cid: Optional(str)):
    for cdic in classdb:
        if cid == cdic["cid"]:
            return cdic


def get_lastfirstmiddle(username: Optional(str)):
    for udic in userdb:
        if username == udic["username"]:
            if udic["middlename"]:
                return (
                    udic["lastname"]
                    + ", "
                    + udic["firstname"]
                    + " "
                    + udic["middlename"]
                )
            else:
                return udic["lastname"] + ", " + udic["firstname"]


def get_class_student_home_actions(username, class_):
    html = '<span class="fawed">'
    html += '<a href="/deregister/%s">Deregister</a>' % class_["cid"]
    html += '</span>'
    
    return Markup(html)

def get_class_available_home_actions(username, class_):
    html = '<span class="fawedfeds">'
    html += '<a href="/register/%s">Register</a>' % class_["cid"]
    html += '</span>'
    
    return Markup(html)


def get_display_available_classes(username: str):
    return [
        (
            class_["subject"],
            get_lastfirstmiddle(class_["mentors"][0]),
            class_["cid"],
            class_["time_desc"],
            get_class_available_home_actions(username, class_),
        )
        for class_ in classdb
        if (username not in class_["mentees"]) and (username not in class_["mentors"])
    ]
def get_class_teacher_home_actions(username, class_):
    html = '<span class="fasedhfiudshli">'
    html += '<a href="/view-students/%s">View students</a>' % class_["cid"]
    html += '</span>'
    
    return Markup(html)


def get_display_learning_classes(username: str):
    return [
        (
            class_["subject"],
            get_lastfirstmiddle(class_["mentors"][0]),
            class_["cid"],
            class_["time_desc"],
            get_class_student_home_actions(username, class_),
        )
        for class_ in classdb
        if username in class_["mentees"]
    ]


def get_display_teaching_classes(username: str):
    return [
        (
            class_["subject"],
            get_lastfirstmiddle(class_["mentors"][0]),
            class_["cid"],
            class_["time_desc"],
            get_class_teacher_home_actions(username, class_),
        )
        for class_ in classdb
        if username in class_["mentors"]
    ]


@app.route("/static/<path:path>", methods=["GET"])
def static_(path: str):
    return send_from_directory("static", path)

@app.route("/view-students/<cid>", methods=["GET"])
def view_students(cid):
    username = check_cookie(request.cookies.get("session-id"))
    if not username:
        return redirect("/login")
    udic = get_udic(username)
    if not username in get_cdic(cid)["mentors"]:
        return "You are not a mentor in this section, you can't view the student list."
    return "\n".join([get_lastfirstmiddle(u) for u in get_cdic(cid)["mentees"]])

@app.route("/register/<cid>", methods=["GET"])
def register(cid):
    username = check_cookie(request.cookies.get("session-id"))
    if not username:
        return redirect("/login")
    udic = get_udic(username)
    if username in get_cdic(cid)["mentees"]:
        return "You are already in this section!"
    else:
        get_cdic(cid)["mentees"].append(username)
        return "Done!"
@app.route("/deregister/<cid>", methods=["GET"])
def deregister(cid):
    username = check_cookie(request.cookies.get("session-id"))
    if not username:
        return redirect("/login")
    udic = get_udic(username)
    try:
        get_cdic(cid)["mentees"].remove(username)
    except ValueError:
        return "You are not in this section, you can't deregister from it!"
    else:
        return "Done!"

@app.route("/", methods=["GET"])
def index():
    username = check_cookie(request.cookies.get("session-id"))
    if not username:
        return redirect("/login")
    udic = get_udic(username)
    # TODO
    return render_template(
        "index.html",
        lastfirstmiddle=get_lastfirstmiddle(username),
        display_learning_classes=get_display_learning_classes(username),
        display_teaching_classes=get_display_teaching_classes(username),
        display_available_classes=get_display_available_classes(username),
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        username = check_cookie(request.cookies.get("session-id"))
        if username:
            return render_template(
                "login.html",
                note=f'Note: You are already logged in as "{username}". Only submit this form to login as another user.',
            )
        return render_template("login.html")
    if not ("username" in request.form and "password" in request.form):
        return render_template(
            "login.html",
            note='Error: Your request does not include the required fields "username" and "password".',
        )
    if not check_login(request.form["username"], request.form["password"]):
        return render_template("login.html", note="Error: Invalid credentials.")
    username = request.form["username"]
    session_id = token_urlsafe(64)
    add_cookie(username, session_id)
    response = make_response(redirect("/"))
    response.set_cookie("session-id", session_id)
    return response


if __name__ == "__main__":
    try:
        app.run(port=8000, debug=True)
    finally:
        print("This should only occur once!")
        print(classdb)
        write_udb()
        write_cdb()

