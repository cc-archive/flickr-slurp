#!/bin/bash

# Script to loop fetching data from the database server,
# fetch images from the service,
# and store them on the repository.

CONFIG_SERVER_ROOT="http://107.170.230.223"

if [ ! -f ./config.sh ]
then
    wget "${CONFIG_SERVER_ROOT}/config.sh"
fi

source ./config.sh

if [ ! -f "./${FILE_SERVER_SSH_KEY}" ]
then
    wget "${CONFIG_SERVER_ROOT}/${FILE_SERVER_SSH_KEY}"
    chmod 400 "${FILE_SERVER_SSH_KEY}"
fi

DOWNLOAD_DIR="${WORK_DIR}/flickr"
ERROR_LOG="${WORK_DIR}/downloader-error.log"
# The script to fetch image urls (or the stop command) from
DATA_SCRIPT="${DATA_SERVER}/more-image-ids.php"
# The file in which to save each batch of image urls to doanload
TASKS_FILE="$WORK_DIR/tasks.csv"
METADATA_FILE="$WORK_DIR/metadata.csv"
IMAGES_FILE="$WORK_DIR/image_urls.txt"

# The command to wget images efficiently from flickr
WGET_IMAGES="xargs -n 1 -P 12 wget -q -P ${DOWNLOAD_DIR}"

#FIXME use ip
MY_ID=`cat /etc/hostname`

# Write the log message to the local log file and to the one on the db server

function log {
    msg="$(date) - ${MY_ID}: ${1}"
    echo "$msg"
    echo "$msg" >> "${ERROR_LOG}"
#    echo "$msg" | ${FILE_SERVER_LOG_COMMAND}
}

# Check for errors, log and exit if found

function check_error {
    err="${1}"
    context="${2}"
    if [ $err -ne 0 ]; then
        log "EXIT DUE TO ERROR: $r - ${context}"
        exit $1
    fi
}

# we're hitting videos around 9/100 million that redirect badly to photo...play
# so skip videos for now

function remove_videos {
    grep -v "video" "${TASKS_FILE}" > "${TASKS_FILE}.stripped"
    mv "${TASKS_FILE}.stripped" "${TASKS_FILE}"
}

# Loop forever until we get an error or signal
# We will get a 404 when there are no more image ids so this will exit,
# although we don't check for 404s explicitly.

# Note the checking to see if we are continuing after being interrupted

while true
do
    # tickle can't do this as we can't add it, tickle doesn't self-update
    if [ ! -f "${IAS3UPLOAD}" ]
    then
        wget --output-document="${IAS3UPLOAD}" \
             "http://${DATA_SERVER}/ias3upload.pl"
        chmod +x "${IAS3UPLOAD}"
        
    fi
    # Clean up ready to start
    rm -rf "${DOWNLOAD_DIR}"/*
    # If we crashed with a zero-length urls file, remove it
    if [ ! -s "${TASKS_FILE}" ]
    then
        rm -f "${TASKS_FILE}"
    fi
    # If we weren't interrupted before we finished, get new file list
    if [ ! -f "${TASKS_FILE}" ]
    then
       # Fetch the next block of image file urls to fetch
       wget --output-document="${TASKS_FILE}" "${DATA_SCRIPT}"
       check_error $? "wget tasks"
    fi
    # Remove videos for now
    remove_videos
    # Extract metadata and urls files
    perl -nle 'print $1 if /(.+?)(,https:\/\/[^,]+)?$/;' "${TASKS_FILE}" \
         > "${METADATA_FILE}"
    perl -nle 'print $1 if /(https:\/\/[^,]+)$/;' "${TASKS_FILE}" \
         > "${IMAGES_FILE}"
    # Download all the files to our working folder
    cat "${IMAGES_FILE}" | ${WGET_IMAGES}
    check_error $? "wget images"
    # Upload all the images
    #export IAS3KEYS="${IAS3_KEYS}"
    "${IAS3UPLOAD}" -k "${IAS3_KEYS}" --no-derive "${METADATA_FILE}"
    check_error $? "upload images"
    exit
    # Clean up ready for next time
    rm -f "${TASKS_FILE}"
    rm -f "${METADATA_FILE}"
    rm -f "${IMAGES_FILE}"
done
