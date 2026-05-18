import pytest
import sqlite3
import mssqltest.sqlextractor


class TestSQLExtractor:

	@pytest.fixture(scope='class')
	def db_conn(self):
		conn = sqlite3.connect(':memory:')
		cursor = conn.cursor()
		cursor.execute(
			'CREATE TABLE accession (id TEXT PRIMARY KEY)'
		)
		conn.commit()
		yield conn
		conn.close()

	def test_constructor(self):
		cursor = db_conn.cursor()
		cursor.execute(
			'SELECT accession.id FROM accession'
		)
