from __future__ import print_function

import mysql.connector
from mysql.connector import errorcode
import yaml

# scp -3 rob@search:/var/www/html/queries.txt root@107.170.230.223:/root/

# Remove http lines, empty lines, script injection, lines starting with ascii art, lines startig with ascci art that doesn't play nicely with single quotes, sort and unique, reshuffle
# grep -v http queries.txt | grep -v '^[[:space:]]*$' | grep -v "}" | grep -v '^[,`~^<>,.?/_=|\\:;-]' | grep -v "^'" | sort | uniq -u | shuf > qqq.txt
# THEN OPEN IN TEXT EDITOR AND REMOVE ASCII ART LINES AT START.


CREATES = [
"""
CREATE TABLE query_shards (
       query_id     INT           UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT,
       query        VARCHAR(255)  UNIQUE NOT NULL,
       worker       VARCHAR(20),
       page_total   INT           NOT NULL DEFAULT 0,
       page_current INT           NOT NULL DEFAULT 1
);
""","""
CREATE INDEX query_index on query_shards (query);
 ""","""
CREATE TABLE flickr_photos_from_queries (
       photo_id     BIGINT            UNSIGNED NOT NULL PRIMARY KEY,
       license      TINYINT           UNSIGNED NOT NULL,
       original_url VARCHAR(255)      NOT NULL,
       owner        VARCHAR(14)       NOT NULL,
       owner_name   VARCHAR(255)      NOT NULL,
       title        VARCHAR(255)      NOT NULL,
       accessed     TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP
);
 ""","""
CREATE INDEX query_photos_url_index on flickr_photos_from_queries (original_url);
"""
]

INSERT_QUERY = \
"""INSERT IGNORE INTO query_shards (query)
    VALUES (%(query)s)"""

def create_tables (cursor):
    print("Creating:")
    for create in CREATES:
        try:
            cursor.execute(create)
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                print("already exists.")
            else:
                print(err.msg)
        else:
            print("OK")

def create_queries (cursor, config):
    print("Inserting queries.")
    with open(config['queries']['filepath']) as query_file:
        for line in query_file:
            # Limit to 255 chars
            query = line.strip()[0:255]
            #print(query)
            cursor.execute(INSERT_QUERY, {'query': query})

if __name__ == '__main__':
    config = yaml.load(open('config.yaml'))
    dbconfig = config['database']
    connection = mysql.connector.connect(user=dbconfig['user'],
                                         password=dbconfig['password'],
                                         host=dbconfig['host'],
                                         database=dbconfig['database'])
    cursor = connection.cursor()
    create_tables(cursor)
    create_queries(cursor, config)
    connection.commit()
    cursor.close()
    connection.close()
