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


app = Flask(__name__)

users = [{"username": "s22537", "uid": "b38adf61-5e7d-4835-812f-364559dba4d4", "password": "936d6f62ed697a935e8a1b9808f26f63018e5c7c54ec1a873aa3457a78f905160b8b74df9cc270e8b652a51d31469eefc41a48e001a5dbe94cbb451c8c6149f4", "cookies": set()}]

def check_login(username: str, password: str) -> Optional(str):
    for udic in users:
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
    for udic in users:
        if cookie in udic["cookies"]:
            return udic["uid"]
    return False

def add_cookie(uid: str, cookie: str) -> None:
    for udic in users:
        if uid == udic["uid"]:
            udic["cookies"].add(cookie)
            return None
    raise ValueError(f'User "{uid}" not found')

def get_username(uid: Optional(str)):
    for udic in users:
        if uid == udic["uid"]:
            return udic["username"]

@app.route('/', methods=['GET'])
def index():
    return make_response(request.cookies.get("biscuit"))

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
    app.run(port=8000)

