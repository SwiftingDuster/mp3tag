import os
import re
from sys import argv

from hanziconv import HanziConv
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError
from mutagen import File

argCount = len(argv)
if argCount < 2:
    print("Usage: Mp3Tag.py <filePath | dirPath> [format string] [index]")
    os._exit(0)

targetPath = os.getcwd() if argv[1] == '.' else argv[1]

convertFormatString = '%artist% - %title%'
if argCount > 2:
	convertFormatString = convertFormatString if argv[2] == '.' else argv[2].lower()

if not os.path.exists(targetPath):  # The path specified doesn't exist
    print("Error: Given path does not exist.")
    os._exit(0)
# Format string has odd number of % and therefore invalid
elif convertFormatString.count("%") % 2 != 0:
    print("Error: Format string is not valid.")
    os._exit(0)

# Get all formatting placeholders E.g. (%artist%, %title%, %genre%, %album%)
formatterList = re.findall(r"(\%.+?\%)", convertFormatString)

# Check validity of formatting placeholders
for formatter in formatterList:
    if formatter[1:-1] not in EasyID3.valid_keys.keys():
        print(f"ERROR: Formatter '{formatter}' is not valid.")
        os._exit(0)

# Replace all formatters with a regex string and compile it. # %artist% - %title% => \b(.*)\b - \b(.*)\b
convertFormatRegexString = convertFormatString
for formatter in formatterList:
    convertFormatRegexString = convertFormatRegexString.replace(formatter, r"\b(.*)\b") 
convertFormatRegex = re.compile(convertFormatRegexString)

totalCount = 0
processedCount = 0
skippedFilesDict = {}

def skip(filePath, reason):
    global processedCount
    skippedFilesDict[filePath] = reason
    print(reason)
    return

def convert(filePath):
    # Get the file name without extension
    fileNameWithExt = os.path.basename(filePath)

    global processedCount, skippedFilesDict
    
    nameExtTuple = os.path.splitext(fileNameWithExt)
    if (nameExtTuple[1] != ".mp3"): # If not a MP3 file
        reason = f"Skipped non mp3 file: {filePath}\n"
        skip(filePath, reason)
        return

    # Convert traditional chinese to simplified chinese
    fileName = HanziConv.toSimplified(nameExtTuple[0])

    # If file name was modified, reflect the change in the real file.
    newFilePath = os.path.join(os.path.dirname(filePath), f"{fileName}.mp3")
    if filePath != newFilePath:
        os.rename(filePath, newFilePath)
        filePath = newFilePath

    # Capture groups from file name using regex created from provided format string.
    matches = convertFormatRegex.match(fileName)
    
    if (matches == None):
        reason = f"Skipped unmatched file: {filePath}\n"
        skip(filePath, reason)
        return

    try:
        mp3 = EasyID3(filePath)
        mp3.delete() # Delete existing ID3 tag
    except ID3NoHeaderError:
        mp3 = File(filePath, easy=True)
        mp3.add_tags() # Add new ID3 tag
    
    processedCount += 1
    print(f"Processing file {processedCount} of {totalCount}: {filePath}")

    # Apply the values
    for index, value in enumerate(matches.groups()):
        formatter = formatterList[index]
        if formatter == r"%title%":
            mp3["title"] = value
        elif formatter == r"%artist%":
            mp3["artist"]= value
        elif formatter == r"%album%":
            mp3["album"] = value
        elif formatter == r"%genre%":
            mp3["genre"] = value
        elif formatter == r"%comment%":
            mp3["comment"] = value
        elif formatter in EasyID3.valid_keys.keys():
            print(f"ERROR: Formatter '{formatter}' is available but not implemented.")
            return
        print(f"Formatter Interpret: {formatter} ==> {value}")
    print()

    # Save
    mp3.save()

print("========================================")
print(f"Target path: {targetPath}")
print(f"Formatter: {convertFormatString}")
print()

if os.path.isdir(targetPath):
    fileList = [os.path.join(targetPath, fileName) for fileName in os.listdir(targetPath)]
    
    startIndex = 0
    if argCount > 3:
        if argv[3].isnumeric():
            indexRaw = int(argv[3]) - 1
            startIndex =  indexRaw if indexRaw >= 0 and indexRaw < len(fileList) else 0 
            print(f"Starting from file number: {argv[3]}")
        else:
            print(f"ERROR: Start index is not a number: {argv[3]}")
            os._exit(0)

    totalCount = len(fileList[startIndex:])

    for file in fileList[startIndex:]:
        convert(file)
else:
    totalCount = 1
    convert(targetPath)

print(f"Job done for {totalCount} files. Processed: {processedCount}, Skipped: {len(skippedFilesDict)}")
for file in skippedFilesDict.keys():
    print(f"{skippedFilesDict[file]} {file}")
print("========================================")
