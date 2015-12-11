from __future__ import print_function

import mysql.connector
from mysql.connector import errorcode
import yaml

# This is the program that sets up the database.
# It creates tables, and populates the shards table.

TABLES = {
'shards':"""
-- Shards.
-- Actually shard tasks. Pre-populate this before starting.

CREATE TABLE shards (
       shard_id     INT         NOT NULL PRIMARY KEY AUTO_INCREMENT,
       license      TINYINT     NOT NULL,
       characters   CHAR(2)     NOT NULL,
       worker       VARCHAR(20),
       page_total   INT         NOT NULL DEFAULT 0,
       page_current INT         NOT NULL DEFAULT 0
);
""",

'photos': """
-- Stored photo results
-- https://www.flickr.com/services/api/misc.overview.html
-- says IDs should be treated as opaque strings.
-- It does not give the maximum length for these strings.
-- Photo IDs seem to be 11, user ids up to 13. We allow extra in case.
-- original_url is the o url for the work as provided by flickr.
-- We can create the photo page url on flickr using
--    http://flickr.com/photo.gne?id=<photo_id>
-- or with flickr.com/photos/user_id/photo_id
-- so we don't need to store any more for that.

CREATE TABLE photos (
       -- Photo IDs are unique across servers, so we use this as our key
       photo_id     VARCHAR(12)       NOT NULL PRIMARY KEY,
       license      TINYINT           UNSIGNED NOT NULL,
       original_url VARCHAR(255)      NOT NULL,
       owner        VARCHAR(14)       NOT NULL,
       owner_name   VARCHAR(255)      NOT NULL,
       title        VARCHAR(255)      NOT NULL,
       accessed     TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
       filepath     VARCHAR(255)
);
"""

'downloads': """
-- Like the shards table, this is a working table.
-- The downloader scans the photos table for photos that are not in this table
--   then copies the photo_id and original_url into here, proceeding with
--   similar logic to the shard processing.
-- It sets the downloaded status to -1 to indicate that work is in progress.
-- Once the download is complete, the status is set to 0 for OK,
--   or if there is an error a positive error code is set.
-- This is a little opaque but saves space and is vaguely Unixy.

CREATE TABLE downloads (
      photo_id     VARCHAR(12)       NOT NULL PRIMARY KEY,
      downloader   VARCHAR(20)       NOT NULL,
      status       TINYINT           NOT NULL DEFAULT -1,
      started      TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""
}

#FIXME: Grab work with titles in other scripts
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
