#!/usr/bin/python3

import base64
import os, json, sys, re
import unicodedata
import base32768
import encryption

encryptionManager = encryption.EncryptionManager()

SEPARATOR = "︱"


def unicodeToAscii(s):
    #Translate unicode to ascii as best as possible. Eg special spaces to normal spaces, "é" to "e", etc

    s = s.translate(str.maketrans({
        "\u00A0": " ",
        "\u2000": " ",
        "\u2001": " ",
        "\u2002": " ",
        "\u2003": " ",
        "\u2004": " ",
        "\u2005": " ",
        "\u2006": " ",
        "\u2007": " ",
        "\u2008": " ",
        "\u2009": " ",
        "\u200A": " ",
        "\u200B": "",
        "\u202F": " ",
        "\u205F": " ",
        "\u3000": " ",
        "\uFEFF": "",
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2015": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201C": '"',
        "\u201D": '"',
        "\u2026": "...",
    }))

    return unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode('utf-8')

def guidToBase32768(guidStr):
    guidBytes = bytes.fromhex(guidStr.replace("-", ""))
    return base32768.encode(guidBytes)


def isValidYtPlaylistId(playlistId):
    return len(playlistId) in [18, 34] and re.match("^PL[A-Za-z0-9_-]{16,32}$", playlistId) is not None

def isValidYtVideoId(videoId):
    return re.match("^[A-Za-z0-9_-]{11}$", videoId) is not None

def ytPlaylistIdToBase32768(playlistId):
    #Note: video ID to base 32768 is useless because titles are max 100 characters so we won't hit the 255 char limit.
    #Additionally, it is useful to have easy access to the video id.
    if not isValidYtPlaylistId(playlistId):
        raise ValueError("Invalid playlist id '%s'" % (playlistId))
    return base32768.encode(base64.urlsafe_b64decode(playlistId[2:]))

def sanitizeForWindowsFilename(s):
    return s.translate(str.maketrans({
        '"': '\u2033',
        '*': '\uA60E',
        ':': '\u0589',
        '<': '\u227A',
        '>': '\u227B',
        '?': '\uFF1F',
        '|': '\u01C0',
        '/': '\u29F8',
        '\\': '\u29f9',
        "\u0000": " ",
        "\u0001": " ",
        "\u0002": " ",
        "\u0003": " ",
        "\u0004": " ",
        "\u0005": " ",
        "\u0006": " ",
        "\u0007": " ",
        "\u0008": " ",
        "\u0009": " ",
        "\u000A": " ",
        "\u000B": " ",
        "\u000C": " ",
        "\u000D": " ",
        "\u000E": " ",
        "\u000F": " ",
        "\u0011": " ",
        "\u0012": " ",
        "\u0013": " ",
        "\u0014": " ",
        "\u0015": " ",
        "\u0016": " ",
        "\u0017": " ",
        "\u0018": " ",
        "\u0019": " ",
        "\u001A": " ",
        "\u001B": " ",
        "\u001C": " ",
        "\u001D": " ",
        "\u001E": " ",
        "\u001F": " ",
        "\u007F": " ",
    })).strip()


def sanitizeForHtml(s):
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&apos;").replace('"', "&quot;")
    return s

def sanitizeForMarkdown(s, isUrl=False):
    # Escape special characters for Markdown
    s = s.replace("\\", "\\\\")
    if isUrl:
        s = s.replace("&", "%26").replace("<", "%3C").replace(">", "%3E").replace("'", "%27").replace('"', "%22").replace(" ", "%20")
    else:
        s = sanitizeForHtml(s)
    s = re.sub(r'([*_`\[\]\(\)])', r'\\\1', s)
    return s


def writeTextToFile(filename, data, encrypt=False, retention=False):
    writeBytesToFile(filename, data.encode('utf-8'), encrypt=encrypt, retention=retention)

def writeBytesToFile(filename, data, encrypt=False, retention=False):
    #Write data to a temp file then rename it, to be atomic.
    tempFile = "D:/backup_file.tmp"
    if encrypt:
        if not filename.endswith(".enc"):
            raise ValueError("Filename '%s' must end with .enc to encrypt" % (filename))
        data = encryptionManager.encrypt(data)

    with open(tempFile, "wb+") as f:
        f.write(data)

    os.replace(tempFile, filename)


def mirrorDirs(srcDir, destDir, ignoredFiles=[]):
    print("Mirroring files from %s to %s" % (srcDir, destDir))
    
    for root, dirs, files in os.walk(srcDir):
        for file in files:
            srcFile = os.path.join(root, file)
            relPath = os.path.relpath(srcFile, srcDir)
            destFile = os.path.join(destDir, relPath)

            if not os.path.exists(destFile) or os.path.getmtime(srcFile) > os.path.getmtime(destFile):
                if os.path.exists(destFile) and relPath.replace("\\", "/").rstrip("/") in ignoredFiles:
                    raise Exception("File '%s' has been modified but is ignored by the backup .gitignore" % (relPath))
                print("Copying %s to %s" % (srcFile, destFile))
                #os.makedirs(os.path.dirname(destFile), exist_ok=True)
                #shutil.copy2(srcFile, destFile)
