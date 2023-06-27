INPUT_FILE=$1
OUTPUT_FILE=$2
FILENAME=${INPUT_FILE%.*}

# important: some evaluation scripts require the creation date metadata info, so ffmpeg needs to copy them (-map_metadata 0)

# convert to mp4 (and remove audio)
ffmpeg -y -i $INPUT_FILE -map_metadata 0 -an $FILENAME"_pre.mp4"

# convert to mp4 (and remove audio) and rotate 90 deg
# ffmpeg -y -i $INPUT_FILE -vf "transpose=1" -an $FILENAME"_pre.mp4"

# downscale
ffmpeg -y -i $FILENAME"_pre.mp4" -map_metadata 0 -filter:v scale=960:-1 -c:a copy $FILENAME"_960px_downscale.mp4"
rm $FILENAME"_pre.mp4"