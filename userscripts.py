#!/usr/bin/python3

import sqlite3
import os
import json
import traceback
import snappy
import config
import utils
import re

class Userscripts:

    def __init__(self):
        self.USERSTYLES_DB = "C:/Users/Zezombye/AppData/Roaming/Mozilla/Firefox/Profiles/r530li2w.default/storage/default/moz-extension+++9ecb77ed-7477-49b7-a0e8-f9e8579eeb4b/idb/489858440shtsyil.sqlite"

        self.USERSCRIPTS_DB = "C:/Users/Zezombye/AppData/Roaming/Mozilla/Firefox/Profiles/r530li2w.default/storage/default/moz-extension+++89947469-5500-4ab3-b43b-6c2924c35bc8^userContextId=4294967295/idb/3647222921wleabcEoxlt-eengsairo.sqlite"

        self.userstylesBackupDir = config.BACKUP_DIR+"userstyles/"
        self.userscriptsBackupDir = config.BACKUP_DIR+"userscripts/"


    def parseUserstyleData(self, data):
        #No idea what the format is. Some kind of BSON but not BSON. Weird.
        #It uses FFFF as a delimiter, so we can just seek the sourceCode attribute.
        sourceCodeStart = data.find(b"\xFF\xFF\x73\x6F\x75\x72\x63\x65\x43\x6F\x64\x65\x00\x00\x00\x00\x00\x00")
        if sourceCodeStart == -1:
            raise ValueError("Source code not found in userstyle data")
        sourceCodeStart += 0x12
        #Next 4 bytes are the length of the source code
        sourceCodeLength = int.from_bytes(data[sourceCodeStart:sourceCodeStart+2], "little")
        #print("Source code length:", sourceCodeLength)
        sourceCodeStart += 2
        if data[sourceCodeStart:sourceCodeStart+2] == b"\x00\x00":
            encoding = "utf-16"
            sourceCodeLength *= 2 # UTF-16, so length in bytes is double the character count
        elif data[sourceCodeStart:sourceCodeStart+2] == b"\x00\x80":
            encoding = "utf-8"
        else:
            raise ValueError("Unknown encoding in userstyle data: {}".format(data[sourceCodeStart:sourceCodeStart+2]))
        sourceCodeStart += 2
        if data[sourceCodeStart:sourceCodeStart+4] != b"\x04\x00\xFF\xFF":
            raise ValueError("Magic number not found at expected position in userstyle data")
        sourceCodeStart += 4
        sourceCodeEnd = sourceCodeStart + sourceCodeLength

        if sourceCodeEnd > len(data):
            raise ValueError("Source code length %s exceeds data length" % (sourceCodeLength))
        

        sourceCode = data[sourceCodeStart:sourceCodeEnd].decode(encoding)

        while data[sourceCodeEnd] == 0x00:
            sourceCodeEnd += 1 #skip padding null bytes

        if data[sourceCodeEnd:sourceCodeEnd+0x20] != b"\x0B\x00\x00\x80\x04\x00\xFF\xFF\x75\x73\x65\x72\x63\x73\x73\x44\x61\x74\x61\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\xFF\xFF":
            raise ValueError("Binary data footer not found at position " + hex(sourceCodeEnd))
        
        if not sourceCode.startswith("/* ==UserStyle=="):
            raise ValueError("Userstyle does not start with expected header")
        
        #Check if userstyle ends with } or */ to detect potential corruption
        if not re.search(r"(\}|\*/)\s*$", sourceCode):
            raise ValueError("Userstyle seems corrupted, does not end with expected footer: end is '{}'".format(sourceCode[-20:]))
        
        return sourceCode
    

    def parseUserscriptData(self, data):
        #Userscripts are in a weird binary format but it seems there is a 0x48 bytes header and a constant footer with variable length for padding
        data = data[0x48:]

        userscript = data.decode("utf-16")

        userscriptFooter = "\u0013\uFFFF"

        if not userscript.startswith("// ==UserScript=="):
            raise ValueError("Userscript does not start with expected header")
        
        if not userscript.endswith(userscriptFooter):
            raise ValueError("Userscript does not end with expected footer")
        
        userscript = userscript[:-len(userscriptFooter)]
        userscript = userscript.rstrip("\0")

        return userscript


    def backup(self):
        if not os.path.exists(self.userstylesBackupDir):
            os.makedirs(self.userstylesBackupDir)
        if not os.path.exists(self.userscriptsBackupDir):
            os.makedirs(self.userscriptsBackupDir)

        print("Backing up userstyles")

        if not os.path.exists(self.USERSTYLES_DB):
            raise FileNotFoundError("Userstyles db file not found")
        
        nbUserstyles = 0
        with sqlite3.connect(self.USERSTYLES_DB) as conn:
            cursor = conn.cursor()
            cursor.execute("select object_store_id, key, data from object_data")
            for row in cursor:
                id = row[1].hex()

                try:
                    data = snappy.decompress(row[2])
                    userstyle = self.parseUserstyleData(data)
                except Exception:
                    raise Exception("Error parsing userstyle '{}': {}".format(id, traceback.format_exc()))
                
                userstyleName = re.search(r"^@name\s+(.+)$", userstyle, re.MULTILINE)
                if not userstyleName:
                    raise ValueError("Could not find userstyle name for '{}'".format(id))
                
                userstyleName = userstyleName.group(1).strip()[0:150]
                
                filename = utils.sanitizeForWindowsFilename(userstyleName) + utils.SEPARATOR + id + ".user.css"

                for file in os.listdir(self.userstylesBackupDir):
                    if file != filename and file.endswith(utils.SEPARATOR + id + ".user.css"):
                        print("Renaming userstyle '%s' to '%s'" % (file, filename))
                        os.rename(self.userstylesBackupDir + file, self.userstylesBackupDir + filename)

                print("Saving userstyle '%s'" % (filename))

                with open(self.userstylesBackupDir+filename, "w+", encoding="utf-8", newline="\n") as file:
                    file.write(userstyle)
                nbUserstyles += 1

        if nbUserstyles == 0:
            raise Exception("No userstyles found in the database")
        
        print("Saved {} userstyles".format(nbUserstyles))

        print("Backing up userscripts")
        if not os.path.exists(self.USERSCRIPTS_DB):
            raise FileNotFoundError("Userscripts db file not found")

        nbUserscripts = 0

        with sqlite3.connect(self.USERSCRIPTS_DB) as conn:
            cursor = conn.cursor()
            cursor.execute("select object_store_id, key, data from object_data where key like '0Atpvsdf$%'")
            for row in cursor:
                key = "".join([chr(b-1) for b in row[1]])
                key = key[len("/@source#"):]
                
                try:
                    data = snappy.decompress(row[2])
                    userscript = self.parseUserscriptData(data)
                except Exception:
                    raise Exception("Error parsing userscript '{}': {}".format(key, traceback.format_exc()))
                
                userscriptName = re.search(r"^// @name\s+(.+)$", userscript, re.MULTILINE)
                if not userscriptName:
                    raise ValueError("Could not find userscript name for '{}'".format(key))
                userscriptName = userscriptName.group(1).strip()
                
                userscriptMatch = re.search(r"^// @match\s+(.+)$", userscript, re.MULTILINE)
                if not userscriptMatch:
                    raise ValueError("Could not find userscript match for '{}'".format(key))
                userscriptMatch = userscriptMatch.group(1).strip()
                userscriptMatch = re.sub(r"^https?://(www\.)?", "", userscriptMatch).split("/")[0]

                name = (userscriptMatch + utils.SEPARATOR + userscriptName)[0:150]
                key = utils.guidToBase32768(key)
                filename = utils.sanitizeForWindowsFilename(name) + utils.SEPARATOR + key + ".user.js"

                for file in os.listdir(self.userscriptsBackupDir):
                    if file != filename and file.endswith(utils.SEPARATOR + key + ".user.js"):
                        print("Renaming userscript '%s' to '%s'" % (file, filename))
                        os.rename(self.userscriptsBackupDir + file, self.userscriptsBackupDir + filename)

                print("Saving userscript '%s'" % (filename))
                with open(self.userscriptsBackupDir+utils.sanitizeForWindowsFilename(filename), "w+", encoding="utf-8", newline="\n") as file:
                    file.write(userscript)
                nbUserscripts += 1

        if nbUserscripts == 0:
            raise Exception("No userscripts found in the database")
        
        print("Saved {} userscripts".format(nbUserscripts))


if __name__ == "__main__":
    userscripts = Userscripts()
    userscripts.backup()
    print("Backup completed successfully.")
