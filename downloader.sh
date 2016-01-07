#/bin/bash

# Script to loop fetching image IDs from the databse server,
# fetch them from the image service,
# and store them on the file server.

# Doesn't work with symlinked scripts
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

source "${DIR}/config.sh"

DOWNLOAD_DIR="${WORK_DIR}/downloads/"
DIRECTORY_STRUCTURE_ROOT="${WORK_DIR}/flickr"
REMOTE_DIRECTORY_STRUCTURE_ROOT="${FILE_SERVER_DIR}/flickr/"
ERROR_LOG="${WORK_DIR}/downloader-error.log"
REMOTE_ERROR_LOG="${FILE_SERVER_DIR}/downloader-error.log"
# The script to fetch image urls (or the stop command) from
DATA_SCRIPT="${DATA_SERVER}/more-image-ids.php"
# The file in which to save each batch of image urls to doanload
URLS_FILE="$WORK_DIR/file_urls.txt"

PADDING="00000000000"

SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

DATA_SERVER_LOG_COMMAND=\
"ssh ${SSH_OPTS} \"${DATA_SERVER}\" 'cat >> ${REMOTE_ERROR_LOG}'"
# The command to copy images to the file server.
# Note that the -o allows man-in-the-middle attacks, but we need to run this
# without human intervention.
# The alternative would be to .
SCP_ARGS="-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"
SCP="scp $SCP_ARGS -i $FILE_SERVER_SSH_KEY -r ${SSH_OPTS}"
# The command to wget images efficiently from flickr
WGET_IMAGES="xargs -n 1 -P 8 wget -q -P ${DOWNLOAD_DIR}"

#FIXME use ip
MY_ID=`cat /etc/hostname`

# Write the log message to the local log file and to the one on the db server

function log {
    msg="$(date) - ${MY_ID}: ${1}"
    echo "$msg"
    echo "$msg" >> "${ERROR_LOG}"
    echo "$msg" | ${DATA_SERVER_LOG_COMMAND}
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

# Move all files to a deep directory structure, creating directories as needed

function move_files_to_directories {
    for f in $(ls "${DOWNLOAD_DIR}" )
    do
        file_num="${f%%_*}"
        p=`printf "%s%s" "${PADDING:${#file_num}}" "${file_num}"`
        dir="${DIRECTORY_STRUCTURE_ROOT}/${p:0:1}/${p:1:1}/${p:2:1}/${p:3:1}/${p:4:1}/${p:5:1}/${p:6:1}/${p:7:1}/${p:8:1}/${p:9:1}/${p:10:1}/"
        mkdir -p "${dir}"
        mv "${DOWNLOAD_DIR}/${f}" "${dir}"
    done
}

# Loop forever until we get an error.
# We will get a 404 when there are no more image ids so this will exit,
# although we don't check for 404s explicitly.

while true
do
    # Fetch the next block of image file urls to fetch
    wget --output-document="$URLS_FILE" "${DATA_SCRIPT}"
    check_error $? "wget urls"
    # Download all the files to our working folder
    cat "${URLS_FILE}" | ${WGET_IMAGES}
    check_error $? "wget images"
    # Make a nice filesystem friendly directory structure for the files
    move_files_to_directories
    # Copy the files to the file server, deleting as we go
    $SCP "${LOCAL_FILE_ROOT}" \
         "${FILE_SERVER}:${REMOTE_DIRECTORY_STRUCTURE_ROOT}"
    check_error $? "scp images"
    # Clean up ready for next time
    rm -f "${URLS_FILE}"
    rm -rf "${DOWNLOAD_DIR}/*"
done
