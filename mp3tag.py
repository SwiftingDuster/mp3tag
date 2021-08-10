import argparse
import os
import re

from mutagen import File
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError

parser = argparse.ArgumentParser(
    description="Extract mp3 data from filename and write it to the file's metadata.",
    epilog="Usage: mp3tag.py <filePath | dirPath> -f [format string]",
)

parser.add_argument("path", help="Folder containing mp3 files, or a single mp3 file.")
parser.add_argument(
    "-f",
    "--format",
    default="%artist% - %title%",
    help="Filename format used to convert.",
)
args = parser.parse_args()

target_path = os.getcwd() if args.path == "." else args.path
format_string = args.format.lower()

# Path and format string validation
if not os.path.exists(target_path):
    # The path specified doesn't exist
    print("Error: Given path does not exist.")
    exit(1)
elif "%" not in format_string or format_string.count("%") % 2 != 0:
    # Format string has odd number of % and therefore invalid
    print("Error: Format string is not valid.")
    exit(1)

# Full list of metadata keys from EasyID3.valid_keys.keys()
# 'album', 'bpm', 'compilation', 'composer', 'copyright', 'encodedby', 'lyricist', 'length', 'media',
# 'mood', 'title', 'version', 'artist', 'albumartist', 'conductor', 'arranger', 'discnumber',
# 'organization', 'tracknumber', 'author', 'albumartistsort', 'albumsort', 'composersort', 'artistsort',
# 'titlesort', 'isrc', 'discsubtitle', 'language', 'genre', 'date', 'originaldate', 'performer:*',
# 'musicbrainz_trackid', 'website', 'replaygain_*_gain', 'replaygain_*_peak', 'musicbrainz_artistid',
# 'musicbrainz_albumid', 'musicbrainz_albumartistid', 'musicbrainz_trmid', 'musicip_puid',
# 'musicip_fingerprint', 'musicbrainz_albumstatus', 'musicbrainz_albumtype', 'releasecountry',
# 'musicbrainz_discid', 'asin', 'performer', 'barcode', 'catalognumber', 'musicbrainz_releasetrackid',
# 'musicbrainz_releasegroupid', 'musicbrainz_workid', 'acoustid_fingerprint', 'acoustid_id'

# Get all formatting placeholders in between % signs. E.g. %artist%, %title%, %genre%, %album%
formatters = re.findall(r"(\%.+?\%)", format_string)
# Implemented metadata keys
ACCEPTED_FORMATTERS = ["title", "artist", "album", "genre"]

# Check validity of formatting placeholders
for formatter in formatters:
    if formatter[1:-1] not in ACCEPTED_FORMATTERS:
        print(f"ERROR: Formatter '{formatter}' is not valid.")
        exit(1)


# Replace all formatters with a regex string and compile it. E.g. %artist% - %title% => \b(.*)\b - \b(.*)\b
formatter_regex_str = format_string
for formatter in formatters:
    formatter_regex_str = formatter_regex_str.replace(formatter, r"\b(.*)\b")
convertFormatRegex = re.compile(formatter_regex_str)


# Setup counters
total_count = 0
processed_count = 0
error_reason_dict = {}


def convert(file_path):
    global processed_count

    # Get the file name without extension
    filename_with_ext = os.path.basename(file_path)

    try:
        from hanziconv import HanziConv
    except ImportError:
        pass
    else:
        # Convert traditional chinese to simplified chinese
        file_name = HanziConv.toSimplified(os.path.splitext(filename_with_ext)[0])

        # If file name was modified, write the change to the file.
        newFilePath = os.path.join(os.path.dirname(file_path), f"{file_name}.mp3")
        if file_path != newFilePath:
            os.rename(file_path, newFilePath)
            file_path = newFilePath

    # Capture groups from file name using regex created from provided format string.
    matches = convertFormatRegex.match(file_name)

    if matches == None:
        error_reason_dict[
            filename_with_ext
        ] = "Check that filename matches with format pattern."
        processed_count += 1
        return

    try:
        mp3 = EasyID3(file_path)
        mp3.delete()  # Delete existing ID3 tag
    except ID3NoHeaderError:
        mp3 = File(file_path, easy=True)
        mp3.add_tags()  # Add new ID3 tag

    processed_count += 1

    print(f"Processed file {processed_count} of {total_count}: {filename_with_ext}")

    # Apply the values
    for index, value in enumerate(matches.groups()):
        formatter = formatters[index]
        if formatter == "%title%":
            mp3["title"] = value
        elif formatter == "%artist%":
            mp3["artist"] = value
        elif formatter == "%album%":
            mp3["album"] = value
        elif formatter == "%genre%":
            mp3["genre"] = value
        elif formatter in ACCEPTED_FORMATTERS:
            print(f"ERROR: Formatter '{formatter}' not implemented.")
            return

    # Save
    mp3.save()


print("========================================")
print(f"Target path: {target_path}")
print(f"Formatter: {format_string}")
print()

if os.path.isdir(target_path):
    fileList = [
        os.path.join(target_path, file_name)
        for file_name in os.listdir(target_path)
        if file_name.endswith(".mp3")
    ]
    total_count = len(fileList)
    for file in fileList:
        convert(file)
else:
    total_count = 1
    convert(target_path)

print(
    f"Job done for {total_count} files. Processed: {processed_count}, Errored: {len(error_reason_dict)}"
)
for file in error_reason_dict.keys():
    print(f"{error_reason_dict[file]} {file}")
print("========================================")
