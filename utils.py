#!/usr/bin/python3

import os, json, sys, re
import base32768

SEPARATOR = "︱"

def guidToBase32768(guidStr):
    guidBytes = bytes.fromhex(guidStr.replace("-", ""))
    return base32768.encode(guidBytes)

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
    })).strip()
