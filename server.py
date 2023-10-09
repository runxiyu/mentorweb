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
from flask import Flask, render_template, request, redirect, abort, send_from_directory, make_response
from datetime import datetime
from time import time
from hashlib import sha512
from secrets import token_urlsafe
import json

app = Flask(__name__)


global userdb

def read_cdb() -> None:
    try:
        dbfile = open("cdb.json", "r")
    except FileNotFoundError:
        udb = []
    else:
        udb = json.load(dbfile)
        assert type(udb) is list
    finally:
        dbfile.close()
    return udb

def write_cdb() -> None:
    try:
        dbfile = open("cdb.json", "w")
        json.dump(userdb, dbfile, indent='\t')
    finally:
        dbfile.close()

def read_udb() -> None:
    try:
        dbfile = open("udb.json", "r")
    except FileNotFoundError:
        udb = []
    else:
        udb = json.load(dbfile)
        assert type(udb) is list
    finally:
        dbfile.close()
    return udb

def write_udb() -> None:
    try:
        dbfile = open("udb.json", "w")
        json.dump(userdb, dbfile, indent='\t')
    finally:
        dbfile.close()

userdb = read_udb()
coursedb = read_cdb()

def check_login(username: str, password: str) -> Optional(str):
    for udic in userdb:
        if udic["username"] == username:
            try:
                salted = (udic["uid"] + ":" + password).encode("utf-8")
            except UnicodeEncodeError:
                return None
            if sha512(salted).hexdigest() == udic["password"]:
                return udic["uid"]
            else:
                return None
    return None

def check_cookie(cookie: Optional(str)) -> Optional(str):
    for udic in userdb:
        if cookie in udic["cookies"]:
            return udic["uid"]
    return False

def add_cookie(uid: str, cookie: str) -> None:
    for udic in userdb:
        if uid == udic["uid"]:
            udic["cookies"].append(cookie)
            return None
    raise ValueError(f'User "{uid}" not found')

def get_username(uid: Optional(str)):
    for udic in userdb:
        if uid == udic["uid"]:
            return udic["username"]

def get_udic(uid: Optional(str)):
    for udic in userdb:
        if uid == udic["uid"]:
            return udic

def get_lastfirstmiddle(uid: Optional(str)):
    for udic in userdb:
        if uid == udic["uid"]:
            if udic["middlename"]:
                return udic["lastname"] + ", " + udic["firstname"] + " " + udic["middlename"]
            else:
                return udic["lastname"] + ", " + udic["firstname"]

@app.route('/static/<path:path>', methods=['GET'])
def static_(path):
    return send_from_directory("static", path)

def display_learning_courses(learning_courses):
    return [[learning_course["subject"], get_lastfirstmiddle(learning_course["mentor"]), learning_course["time"]] for learning_course in learning_courses]

@app.route('/', methods=['GET'])
def index():
    uid = check_cookie(request.cookies.get("biscuit"))
    if not uid:
        return redirect('/login')
    udic = get_udic(uid)
    return render_template('index.html', lastfirstmiddle=get_lastfirstmiddle(uid), display_learning_courses=display_learning_courses(udic["learning_courses"]))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "GET":
        uid = check_cookie(request.cookies.get("biscuit"))
        if uid:
            return render_template('login.html', note=f'Note: You are already logged in as "{get_username(uid)}". Only submit this form to login as another user.')
        return render_template('login.html')
    if not ("username" in request.form and "password" in request.form):
        return render_template("login.html", note='Error: Your request does not include the required fields "username" and "password".')
    uid = check_login(request.form["username"], request.form["password"])
    if not uid:
        return render_template("login.html", note='Error: Invalid credentials.')
    response = make_response(redirect('/'))
    biscuit = token_urlsafe(64)
    add_cookie(uid, biscuit)
    response.set_cookie('biscuit', biscuit)
    return response


if __name__ == "__main__":
    try:
        app.run(port=8000, debug=True)
    finally:
        write_udb()

