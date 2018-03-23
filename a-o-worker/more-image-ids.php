<?php

/*

Make sure you:

   CREATE TABLE download_ids_offsets (
       id             INT        UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
       ids_offset     BIGINT     UNSIGNED NOT NULL
   );
   INSERT INTO download_ids_offsets (ids_offset) VALUES (1);

We need that initial (non-)offset.

*/

include(dirname(__FILE__) . '/config.php');

// License to url
$LICENSE_URL = ['',
                'https://creativecommons.org/licenses/by-nc-sa/2.0/',
                'https://creativecommons.org/licenses/by-nc/2.0/',
                'https://creativecommons.org/licenses/by-nc-nd/2.0/',
                'https://creativecommons.org/licenses/by/2.0/',
                'https://creativecommons.org/licenses/by-sa/2.0/',
                'https://creativecommons.org/licenses/by-nd/2.0/',
                'http://flickr.com/commons/usage/',
                'http://www.usa.gov/copyright.shtml',
    ];

$LICENSE_DESC = ['is All Rights Reserved',
                 'is licensed under a <a rel="license" href="https://creativecommons.org/licenses/by-nc-sa/2.0/">Creative Commons Attribution-NonCommercial-ShareAlike 2.0 Generic License</a>',
                 'is licensed under a <a rel="license" href="https://creativecommons.org/licenses/by-nc/2.0/">Creative Commons Attribution-NonCommercial 2.0 Generic License</a>',
                 'is licensed under a <a rel="license" href="https://creativecommons.org/licenses/by-nc-nd/2.0/">Creative Commons Attribution-NonCommercial-NoDerivatives 2.0 Generic License</a>',
                 'is licensed under a <a rel="license" href="https://creativecommons.org/licenses/by/2.0/">Creative Commons Attribution 2.0 Generic License</a>',
                 'is licensed under a <a rel="license" href="https://creativecommons.org/licenses/by-sa/2.0/">Creative Commons Attribution-ShareAlike 2.0 Generic License</a>',
                 'is licensed under a <a rel="license" href="https://creativecommons.org/licenses/by-nd/2.0/">Creative Commons Attribution-NoDerivatives 2.0 Generic License</a>',
                 'has <a rel="license" href="http://flickr.com/commons/usage/">no known copyright restrictions</a>',
                 'is <a rel="license" href="http://www.usa.gov/copyright.shtml">a United States Government Work</a>'];

function image_desc ($photo_id, $lic_num, $owner_id, $owner_name, $title) {
    global $LICENSE_DESC;
    return '<span xmlns:dct="http://purl.org/dc/terms/" href="http://purl.org/dc/dcmitype/StillImage" property="dct:title" rel="dct:type">'
        . $title
        . '</span> by <a xmlns:cc="http://creativecommons.org/ns#" href="https://www.flickr.com/photos/'
        . $owner_id . '/' . $photo_id
        .'" property="cc:attributionName" rel="cc:attributionURL">'
        . $owner_name . '</a> ' . $LICENSE_DESC[$lic_num] . '.';
}

function echo_image_line ($out, $collection, $photo_id, $lic_num, $original_url,
                          $owner_id, $owner_name, $title, $accessed) {
    global $CONTRIBUTOR, $LICENSE_URL;
    // Must be globally unique across archive.org
    $item = $collection . '-' . $photo_id;
    $desc = image_desc ($photo_id, $lic_num, $owner_id, $owner_name, $title);
    fputcsv($out, [$item, '/root/flickr/' . basename($original_url),
                   'image', $collection, $title,
                   $owner_name, '', $desc, $CONTRIBUTOR, $accessed,
                   $LICENSE_URL[$lic_num],
                   // And at the end, the original url for the download client
                   // to use (and remove), so NO HEADER FOR THIS
                   $original_url]);
}

function echo_csv_header () {
    echo '"item","file","mediatype","collection","title","creator","language","description","contributor","date","licenseurl"' . "\n";
}

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
                                   ORDER BY id DESC
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

// exclusive
$end_offset = $start_offset + $IDS_QUANTITY;

// Get a block of photo urls to download

$photo_rows = false;
$select_urls_statement = $dbh->prepare("
SELECT photo_id, license, original_url, owner, owner_name, title, accessed
FROM photos
WHERE id >= " . $start_offset . " AND id  < " . $end_offset);
$ok = $select_urls_statement->execute();
if ($ok === false) {
    error_log("Couldn't select photos for " . $requestor);
    http_response_code(500);
    exit;
}
$photo_rows = $select_urls_statement->fetchAll();
if ($photo_rows === false) {
    error_log("Couldn't fetch all photos for " . $requestor);
    http_response_code(500);
    exit;
}

if (count($photo_rows) == 0) {
    error_log("No more photos for " . $requestor);
    // Not strictly true as future requests should not be made.
    // But easy for humans to understand
    http_response_code(404);
    exit;
}

echo_csv_header();
$out = fopen('php://output', 'w');
foreach ($photo_rows as $row) {
    echo_image_line ($out, $COLLECTION, $row['photo_id'],
                     $row['license'], $row['original_url'],
                     $row['owner'], $row['owner_name'],
                     $row['title'], $row['accessed']);
}
fclose($out);

// Store the offset that the next task should start from
$store_offset_statement = $dbh->prepare("INSERT INTO download_ids_offsets
                                             (ids_offset)
                                             VALUES (:offset)");
$ok = $store_offset_statement->execute([':offset' => $end_offset]);
if ($ok === false) {
    error_log("Couldn't save next offset (" . $end_offset . ") for "
            . $requestor);
    http_response_code(500);
    exit;
}
