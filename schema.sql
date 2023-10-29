CREATE TABLE users (username text primary key not null, argon2 text, cookietime real, cookie text, lastname text, firstname text, middlename text);
CREATE TABLE meetings (mid integer primary key, mentor text, mentee text, time_start integer, time_end integer, notes text);
