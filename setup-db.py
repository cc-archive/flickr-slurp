from __future__ import print_function

import mysql.connector
from mysql.connector import errorcode
import yaml

TABLES = {
'shards':"""
-- Shards.
-- Actually shard tasks. Pre-populate this before starting.

CREATE TABLE shards (
       shard_id     INT         NOT NULL PRIMARY KEY AUTO_INCREMENT,
       license      TINYINT     NOT NULL,
       characters   CHAR(2)     NOT NULL,
       worker       VARCHAR(255),
       page_total   INT         NOT NULL DEFAULT 0,
       page_current INT         NOT NULL DEFAULT 0
);
""",

'photos': """
-- Stored photo results
-- https://www.flickr.com/services/api/misc.overview.html
-- says IDs should be treated as opaque strings.
-- It does not give the maximum length for these strings.
-- So we're using VARCHAR 255, which is inefficient for search but efficient
-- for storage, which at this scale is an acceptable trade-off and if we hit
-- any nsids longer than 15 chars or any photo IDs of more than 12 digits
-- we're set.

CREATE TABLE photos (
       -- Photo IDs are unique across servers, so we use this as our key
       photo_id     VARCHAR(255)      NOT NULL PRIMARY KEY,
       license      CHAR(1)           NOT NULL,
       nsid         VARCHAR(255)      NOT NULL,
       farm         VARCHAR(5)        NOT NULL,
       server       VARCHAR(255)      NOT NULL,
       originalsecret VARCHAR(255)    NOT NULL
);
"""
}

# 1..8 inclusive (0 is ARR)
LICENSES = [str(num) for num in range(1, 9)]
LETTERS = list('abcdefghijklmnopqrstuvwxyz')
NUMBERS = ["{0:02d}".format(num) for num in range(0, 100)]

INSERT_SHARD = \
"""INSERT INTO shards (license, characters, page_current)
    VALUES (%(license)s, %(characters)s, 1)"""

def create_tables (cursor):
    for name, command in TABLES.iteritems():
        try:
            print("Creating table {}: ".format(name), end='')
            cursor.execute(command)
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                print("already exists.")
            else:
                print(err.msg)
        else:
            print("OK")

def create_shards (cursor):
    for lic in LICENSES:
        print("License: {}".format(lic))
        for a in LETTERS:
            for b in LETTERS:
                cursor.execute(INSERT_SHARD,
                               {'license': lic,
                                'characters': "{}{}".format(a, b)})

if __name__ == '__main__':
    config = yaml.load(open('config.yaml'))
    dbconfig = config['database']
    connection = mysql.connector.connect(user=dbconfig['user'],
                                         password=dbconfig['password'],
                                         host=dbconfig['host'],
                                         #unix_socket='/var/run/mysqld/mysqld.sock',
                                         database=dbconfig['database'])
    cursor = connection.cursor()
    create_tables(cursor)
    create_shards(cursor)
    connection.commit()
    cursor.close()
    connection.close()
