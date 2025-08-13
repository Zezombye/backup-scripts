#!/usr/bin/python3

import base64
import os, json, sys, re
import unicodedata
import base32768

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

def sanitizeForMarkdown(s, isUrl=False):
    # Escape special characters for Markdown
    s = s.replace("\\", "\\\\")
    if isUrl:
        s = s.replace("&", "%26").replace("<", "%3C").replace(">", "%3E").replace("'", "%27").replace('"', "%22").replace(" ", "%20")
    else:
        s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&apos;").replace('"', "&quot;")
    s = re.sub(r'([*_`\[\]\(\)])', r'\\\1', s)
    return s
