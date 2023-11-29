CREATE TABLE users (username text primary key not null, argon2 text, cookietime real, cookie text, lastname text, firstname text, middlename text, subjects text);
CREATE TABLE meetings (mid integer primary key, mentor text, mentee text, time_start integer, time_end integer, notes text);
CREATE TABLE subjects (subjectid text primary key not null, subjectname text not null);
