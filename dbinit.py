import sqlite3

conn = sqlite3.connect("udb.db")
cur = conn.cursor()

sql_create_udb = "CREATE TABLE students (username STRING PRIMARY KEY NOT NULL, lastname TEXT, firstname TEXT, middlename TEXT)"
cur.execute(sql_create_udb)

cdb_1 = {
	"subject": "10 Economics \u7ecf\u6d4e",
	"mentors": [
		"s22537"
	],
	"mentees": [
		"s14003"
	],
	"time_desc": "M"
}
cdb_2 = {
	"subject": "10 History \u5386\u53f2",
	"mentors": [
		"s14003"
	],
	"mentees": [
		"s22537"
	],
	"time_desc": "M"
}
cdb_3 = {
	"subject": "10 Chinese \u4e2d\u6587",
	"mentors": [
		"s14003"
	],
	"mentees": [
		"s22537"
	],
	"time_desc": "M"
}

udb_1 = {
	"username": "s22537",
	"salt": "b38adf61-5e7d-4835-812f-364559dba4d4",
	"password": "936d6f62ed697a935e8a1b9808f26f63018e5c7c54ec1a873aa3457a78f905160b8b74df9cc270e8b652a51d31469eefc41a48e001a5dbe94cbb451c8c6149f4",
	"cookies": [
		"HMw3BhWaTjoT8Ue5UVHLkEhxcespmhIO7vOg849cJeX2IzVOp3IByDlxgbpO9k5lFrrrg41D3H7Va4KkDNgZaA",
		"aY5xBxysNRBPRbqBdecf37o_zNMrT_P2ehR05SlpUN6hhavVUj2Hsn2bOdU9FPYmT2q5S4pvwvH1QpVZUH2yKw"
	],
	"learning_courses": [
		{
			"subject": "10 History \u5386\u53f2",
			"mentor": "84e3ff59-8e6c-45b7-980d-9ea914ce9e73",
			"time": "Tuesday CCA2"
		}
	],
	"teaching_courses": [
		{
			"subject": "10 Economics \u7ecf\u6d4e",
			"mentor": "84e3ff59-8e6c-45b7-980d-9ea914ce9e73",
			"time": "Tuesday CCA2"
		}
	],
	"firstname": "Runxi",
	"lastname": "Yu",
	"middlename": "(Run Xi \u4e8e\u6da6\u7199)"
}
udb_2 = {
	"email": "s14003@ykpaoschool.cn",
	"salt": "84e3ff59-8e6c-45b7-980d-9ea914ce9e73",
	"password": "",
	"cookies": [
		""
	],
	"learning_courses": [
		{
			"subject": "10 Economics \u7ecf\u6d4e",
			"mentor": "b38adf61-5e7d-4835-812f-364559dba4d4",
			"time": "Tuesday CCA3"
		}
	],
	"teaching_courses": [
		{
			"subject": "10 History \u5386\u53f2",
			"mentor": "84e3ff59-8e6c-45b7-980d-9ea914ce9e73",
			"time": "Tuesday CCA2"
		}
	],
	"firstname": "Aaron",
	"lastname": "Zhang",
	"middlename": "(Bo Jun \u5f20\u4f2f\u5747)"
}
cdb_1_str = str(cdb_1)
cdb_2_str = str(cdb_2)
cdb_3_str = str(cdb_3)
udb_1_str = str(udb_1)
udb_2_str = str(udb_2)
sql_insert_cdb_1 = f'INSERT INTO cdb VALUES(1, "{cdb_1_str}")'
sql_insert_cdb_2 = f'INSERT INTO cdb VALUES(2, "{cdb_2_str}")'
sql_insert_cdb_3 = f'INSERT INTO cdb VALUES(3, "{cdb_3_str}")'
sql_insert_udb_1 = f'INSERT INTO udb VALUES(22537, "{udb_1_str}")'
sql_insert_udb_2 = f'INSERT INTO udb VALUES(14003, "{udb_2_str}")'
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
