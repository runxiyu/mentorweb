import sqlite3

conn = sqlite3.connect("database_2.db")
cur = conn.cursor()

sql_create_udb = "CREATE TABLE udb (username INTEGER PRIMARY KEY NOT NULL, email TEXT, password TEXT, cookies TEXT, cookietime REAL, firstname TEXT, lastname TEXT, middlename TEXT)"
cur.execute(sql_create_udb)

sql_create_cdb = "CREATE TABLE cdb (cid INTEGER PRIMARY KEY NOT NULL, subject TEXT, mentors TEXT, mentees TEXT, time_desc TEXT)"
cur.execute(sql_create_cdb)

sql_insert_cdb_1 = 'INSERT INTO cdb VALUES(1, "10 Economics \u7ecf\u6d4e", "22537", "14003", "M")'
sql_insert_cdb_2 = 'INSERT INTO cdb VALUES(2, "10 History \u5386\u53f2", "14003", "22537", "M")'
sql_insert_cdb_3 = 'INSERT INTO cdb VALUES(3, "10 Chinese \u4e2d\u6587", "14003", "22537", "M")'
sql_insert_udb_1 = 'INSERT INTO udb VALUES(22537, "s22537@ykpaoschool.cn", "936d6f62ed697a935e8a1b9808f26f63018e5c7c54ec1a873aa3457a78f905160b8b74df9cc270e8b652a51d31469eefc41a48e001a5dbe94cbb451c8c6149f4", "HMw3BhWaTjoT8Ue5UVHLkEhxcespmhIO7vOg849cJeX2IzVOp3IByDlxgbpO9k5lFrrrg41D3H7Va4KkDNgZaA,aY5xBxysNRBPRbqBdecf37o_zNMrT_P2ehR05SlpUN6hhavVUj2Hsn2bOdU9FPYmT2q5S4pvwvH1QpVZUH2yKw", 0, "Runxi", "Yu", "(Run Xi \u4e8e\u6da6\u7199)")'
sql_insert_udb_2 = 'INSERT INTO udb VALUES(14003, "s14003@ykpaoschool.cn", "", "", 0, "Aaron", "Zhang", "(Bo Jun \u5f20\u4f2f\u5747)")'
cur.execute(sql_insert_cdb_1)
cur.execute(sql_insert_cdb_2)
cur.execute(sql_insert_cdb_3)
cur.execute(sql_insert_udb_1)
cur.execute(sql_insert_udb_2)

conn.commit()

sql_search = "SELECT * FROM udb"
cur.execute(sql_search)
lst = cur.fetchall()
print(lst)
