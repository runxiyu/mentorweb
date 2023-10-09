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
global classdb

def read_cdb() -> None:
    try:
        dbfile = open("cdb.json", "r")
    except FileNotFoundError:
        cdb = []
    else:
        cdb = json.load(dbfile)
        assert type(cdb) is list
    finally:
        dbfile.close()
    return cdb

def write_cdb() -> None:
    try:
        dbfile = open("cdb.json", "w")
        json.dump(classdb, dbfile, indent='\t')
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

def get_lastfirstmiddle(username: Optional(str)):
    for udic in userdb:
        if username == udic["username"]:
            if udic["middlename"]:
                return udic["lastname"] + ", " + udic["firstname"] + " " + udic["middlename"]
            else:
                return udic["lastname"] + ", " + udic["firstname"]

@app.route('/static/<path:path>', methods=['GET'])
def static_(path: str):
    return send_from_directory("static", path)

@app.route('/', methods=['GET'])
def index():
    username = check_cookie(request.cookies.get("session-id"))
    if not username:
        return redirect('/login')
    udic = get_udic(username)
    # TODO
    return render_template(
                                'index.html',
                                lastfirstmiddle=get_lastfirstmiddle(username),
                          )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "GET":
        username = check_cookie(request.cookies.get("session-id"))
        if username:
            return render_template('login.html', note=f'Note: You are already logged in as "{username}". Only submit this form to login as another user.')
        return render_template('login.html')
    if not ("username" in request.form and "password" in request.form):
        return render_template("login.html", note='Error: Your request does not include the required fields "username" and "password".')
    if not check_login(request.form["username"], request.form["password"]):
        return render_template("login.html", note='Error: Invalid credentials.')
    username = request.form["username"]
    session_id = token_urlsafe(64)
    add_cookie(username, session_id)
    response = make_response(redirect('/'))
    response.set_cookie('session-id', session_id)
    return response


if __name__ == "__main__":
    try:
        app.run(port=8000, debug=True)
    finally:
        write_udb()
