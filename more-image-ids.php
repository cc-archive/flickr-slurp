<?php

/*

Make sure you:

   CREATE TABLE download_ids_offsets (
       ids_offset     BIGINT         UNSIGNED NOT NULL PRIMARY KEY
   );
   INSERT INTO download_ids_offsets (ids_offset) VALUES (1);

We need that initial (non-)offset.

*/

include dirname(__FILE__) . '/config.php';

// Is this a client we should be talking to?

function allow_request ($requestor) {
    //TODO: Add amazingly secure client check.
    return true;
}

$requestor = $_SERVER['REMOTE_ADDR'];

if(! allow_request($requestor)) {
    error_log('Denying request from ' . $requestor);
    http_response_code(403);
    exit;
}

global $dbh;

$dbh = new PDO($DBDSN, $DBUSER, $DBPASSWORD);

// Where did the last downloader finish?

$offset_statement = $dbh->prepare("SELECT ids_offset FROM download_ids_offsets
                                   ORDER BY ids_offset DESC
                                   LIMIT 1");
$ok = $offset_statement->execute();
if ($ok === false) {
    error_log("Couldn't execute select on count to continue for " . $requestor);
    http_response_code(500);
    exit;
}
$start_offset = $offset_statement->fetchColumn();
if ($start_offset === false) {
    error_log("Couldn't get count to continue column for " . $requestor);
    http_response_code(500);
    exit;
}

// Get a block of photo urls to download

$photo_urls = false;
$select_urls_statement = $dbh->prepare("SELECT original_url
                                       FROM numeric_id_photos
                                       LIMIT " . $IDS_QUANTITY
                                    . " OFFSET " . $start_offset);
$ok = $select_urls_statement->execute();
if ($ok === false) {
    error_log("Couldn't select photos for " . $requestor);
    http_response_code(500);
    exit;
}
$photo_urls = $select_urls_statement->fetchAll();
if ($photo_urls === false) {
    error_log("Couldn't fetch all photos for " . $requestor);
    http_response_code(500);
    exit;
}

if (count($photo_urls) == 0) {
    error_log("No more photos for " . $requestor);
    // Not strictly true as future requests should not be made.
    // But easy for humans to understand
    http_response_code(404);
    exit;
}


array_walk($photo_urls,
           function ($row) { echo $row['original_url'] . "\n"; });

$next_offset = $start_offset + $IDS_QUANTITY;

// Store the offset that the next task should start from
$store_offset_statement = $dbh->prepare("INSERT INTO download_ids_offsets
                                             (ids_offset)
                                             VALUES (:offset)");
$ok = $store_offset_statement->execute([':offset' => $next_offset]);
if ($ok === false) {
    error_log("Couldn't save next offset (" . $next_offset . ") for "
            . $requestor);
    http_response_code(500);
    exit;
}
