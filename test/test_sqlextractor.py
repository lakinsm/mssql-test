import pytest
import sqlite3
import mssqltest.sqlextractor
from sqlglot.lineage import lineage
from pathlib import Path
from pyvisjs import Network


TEST_DIR = Path(__file__).parent
TMP_DIR = '{}/.tmp/'.format(TEST_DIR)


class TestSQLExtractor:

	@pytest.fixture(scope='class', autouse=True)
	def db_conn(self):
		conn = sqlite3.connect(':memory:')
		cursor = conn.cursor()
		cursor.execute('''
			CREATE TABLE 
				accession (
					id TEXT PRIMARY KEY, 
					type TEXT 
				)
		''')
		conn.commit()

		records = [
			('ABC1', 'TypeA'),
			('ABC2', 'TypeB'),
			('ABC3', 'TypeA'),
			('ABC4', 'TypeB'),
			('ABC5', 'TypeC'),
			('ABC6', 'TypeD')
		]
		cursor.executemany('''
			INSERT INTO 
				accession (id, type) 
			VALUES (?, ?)
		''', records)
		conn.commit()

		cursor.execute('''
			CREATE TABLE parent_map ( 
				id TEXT, 
				parentid TEXT, 
				UNIQUE (id, parentid) 
			)
		''')
		conn.commit()

		records = [
			('ABC1', None),
			('ABC2', None),
			('ABC3', 'ABC1'),
			('ABC4', 'ABC1'),
			('ABC5', 'ABC3'),
			('ABC6', 'ABC2')
		]
		cursor.executemany('''
			INSERT INTO 
				parent_map (id, parentid) 
			VALUES (?, ?)
		''', records)
		conn.commit()

		yield conn
		conn.close()
	
	@pytest.fixture(scope='class', autouse=True)
	def find_parent(self):
		recursive_query = '''
			WITH 
			RECURSIVE tree AS
			(
				SELECT
					id,
					parentid,
					0 AS level
				FROM parent_map
				UNION ALL
				SELECT
					tree.id,
					parent_map.parentid,
					tree.level + 1
				FROM tree
				JOIN parent_map
					ON tree.parentid = parent_map.id
				WHERE parent_map.parentid IS NOT NULL
			)
			SELECT
				root.id,
				root.parentid AS rootid
			FROM (
				SELECT
					id,
					parentid,
					MAX(level) AS maxlevel
				FROM tree
				GROUP BY id
			) as root
		'''
		yield recursive_query

	def test_constructor(self, db_conn):
		cursor = db_conn.cursor()
		cursor.execute('''
			SELECT 
				accession.id, 
				accession.type 
			FROM accession
		''')
		rows = cursor.fetchall()
		assert(rows == [
			('ABC1', 'TypeA'),
			('ABC2', 'TypeB'),
			('ABC3', 'TypeA'),
			('ABC4', 'TypeB'),
			('ABC5', 'TypeC'),
			('ABC6', 'TypeD')
		])

		cursor.execute('''
			SELECT 
				parent_map.id, 
				parent_map.parentid 
			FROM parent_map
		''')
		rows = cursor.fetchall()
		assert(rows == [
			('ABC1', None),
			('ABC2', None),
			('ABC3', 'ABC1'),
			('ABC4', 'ABC1'),
			('ABC5', 'ABC3'),
			('ABC6', 'ABC2')
		])
	
	def test_recursion(self, db_conn, find_parent):
		
		cursor = db_conn.cursor()
		cursor.execute(find_parent)
		rows = cursor.fetchall()
		assert(rows == [
			('ABC1', None),
			('ABC2', None),
			('ABC3', 'ABC1'),
			('ABC4', 'ABC1'),
			('ABC5', 'ABC1'),
			('ABC6', 'ABC2')
		])

	def test_recursive_extract(self, find_parent):
		schema = {
			'accession': {
				'id': 'text',
				'type': 'text'
			},
			'parent_map': {
				'id': 'text',
				'parentid': 'text'
			}
		}

		node = lineage(
			column=None,
			sql=find_parent,
			sources=None,
			schema=schema
		)

		for k, v in node.items():
			print('{}\t{}'.format(k, v.name))
			for n in v.walk():
				print('\t-->{}'.format(n.name))


