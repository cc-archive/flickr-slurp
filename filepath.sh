#!/bin/bash

source config.sh

PADDING="00000000000"

filename=$(basename $1)
echo $filename
f=$(perl -e '$a = "'"$filename"'"; $a =~ s/(?<!_o).jpg$/_o.jpg/; print "$a";')
echo $f
file_num="${f%%_*}"
p=`printf "%s%s" "${PADDING:${#file_num}}" "${file_num}"`
dir="flickr/${p:0:1}/${p:1:1}/${p:2:1}/${p:3:1}/${p:4:1}/${p:5:1}/${p:6:1}/${p:7:1}/${p:8:1}/${p:9:1}/${p:10:1}"
echo "${FILE_SERVER_DIR}/${dir}/${f}"
