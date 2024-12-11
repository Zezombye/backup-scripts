#!/usr/bin/python3

import os
import json
import shutil
import time
import unicodedata
import re
import base32768
import utils
import youtube
import config
import requests

class Notion():

    def __init__(self):
        self.notionTokenFile = "C:/Users/Zezombye/notion.owo"
        self.notionCookieFile = "C:/Users/Zezombye/notion_cookie.owo"

        with open("notion_settings.json", "r") as f:
            notionSettings = json.loads(f.read())

        self.PRIVATE_SPACE_ID = notionSettings["privateSpaceId"]
        self.BACKUP_DIR = config.BACKUP_DIR + "/notion/"

        with open(self.notionTokenFile, "r") as f:
            self.notionToken = f.read().strip()
        with open(self.notionCookieFile, "r") as f:
            self.notionCookie = f.read().strip()

        self.session = requests.session()
        self.session.headers = {"Cookie": self.notionCookie, **notionSettings["headers"]}

        self.youtube = youtube.Youtube()


    def make_request(self, method, url, data=None):
        r = self.session.request(method, url, json=data)
        if not r.ok:
            print(url)
            print(r.status_code)
            print(r.text)
            exit(1)

        with open("debug/notion_"+url.replace("https://www.notion.so/api/v3/", "").replace("/", "_")+".json", "w+", encoding="utf-8") as f:
            f.write(json.dumps(r.json(), indent=4, ensure_ascii=False))

        return r.json()

    def getPrivatePages(self):
        r = self.make_request("post", "https://www.notion.so/api/v3/getUserSharedPagesInSpace", {
            "includeDeleted": False,
            "spaceId": self.PRIVATE_SPACE_ID,
        })

        pages = {}

        for block in r["recordMap"]["block"].values():
            block = block["value"]["value"]
            if block["type"] != "page" or not block["alive"]:
                continue

            pages[block["id"]] = {
                "id": block["id"],
                "title": block["properties"]["title"][0][0],
                "parentId": block["parent_id"] if block["parent_id"] != self.PRIVATE_SPACE_ID else None,
                "ytVideoIds": [],
                "ytPlaylistIds": [],
                "createdTimestampMs": block["created_time"],
                "lastEditedTimestampMs": block["last_edited_time"],
            }

        return pages

    def getPageBlocks(self, pageId, pageTitle):
        print("Getting page blocks of '%s' (%s)" % (pageId, pageTitle))

        blocks = []
        cursorStack = []
        while True:
            r = self.make_request("post", "https://www.notion.so/api/v3/loadCachedPageChunkV2", {
                "page": {
                    "id": pageId,
                    "spaceId": self.PRIVATE_SPACE_ID,
                },
                "verticalColumns": False,
                "cursor": {"stack": cursorStack},
                "limit": 30,
                "omitExistingRecordVersions": [],
            })

            blocks.extend([b["value"]["value"] for b in r["recordMap"]["block"].values() if "value" in b["value"] and b["value"]["value"]["id"] not in [b2["id"] for b2 in blocks]])

            if len(r["cursors"]) == 0:
                break
            else:
                cursorStack = r["cursors"][0]["stack"]

            time.sleep(0.5)

        return blocks


    def getPageDir(self, page):
        pageIdBase32768 = utils.guidToBase32768(page["id"])
        pageDir = utils.sanitizeForWindowsFilename(page["title"]+utils.SEPARATOR+pageIdBase32768)
        return pageDir

    def getPagePath(self, pages, pageId):
        pageDir = self.getPageDir(pages[pageId])
        if pages[pageId]["parentId"] is None:
            return pageDir

        elif pages[pageId]["parentId"] in pages:
            return self.getPagePath(pages, pages[pageId]["parentId"]) + "/" + pageDir

        else:
            raise ValueError("Could not find parent id of page %s" % (pages[pageId]))


    def backupPages(self, pages):

        pageIds = sorted(list(pages.keys()), key=lambda x: (pages[x]["depth"], pages[x]["path"]))

        for pageId in pageIds:
            print("Backing up page %s ('%s')" % (pageId, pages[pageId]["path"]))
            pagePath = self.getPagePath(pages, pageId)

            targetDir = os.path.join(self.BACKUP_DIR, pagePath)

            # Check if any directories end with the specific identifier
            for root, dirs, _ in os.walk(self.BACKUP_DIR):
                for dirName in dirs:
                    dirPath = os.path.join(root, dirName).replace("\\", "/")
                    # Check if the directory ends with the required identifier
                    if dirName.endswith(utils.SEPARATOR + utils.guidToBase32768(pageId)) and dirPath != targetDir:

                        print("Page at '%s' has moved or been renamed, moving it to '%s'" % (dirPath, targetDir))

                        shutil.move(dirPath, targetDir)


            if not os.path.exists(targetDir):
                print("Creating directory '%s' for page id '%s'" % (targetDir, pageId))
            os.makedirs(targetDir, exist_ok=True)

            with open(targetDir+"/_page.json", "w+", encoding="utf-8") as f:
                f.write(json.dumps(pages[pageId], indent=4, ensure_ascii=False))

            pages[pageId]["ytVideoIds"] = list(set(pages[pageId]["ytVideoIds"]))
            for ytVideoId in pages[pageId]["ytVideoIds"]:
                print("Downloading yt video '%s'" % (ytVideoId))
                self.youtube.download_video(ytVideoId, targetDir)

            pages[pageId]["ytPlaylistIds"] = list(set(pages[pageId]["ytPlaylistIds"]))
            for ytPlaylistId in pages[pageId]["ytPlaylistIds"]:
                print("Downloading yt playlist '%s'" % (ytPlaylistId))
                self.youtube.download_playlist(ytPlaylistId, targetDir)


    def backupAllPages(self):

        #Todo: we can speed up the process and make the logs less verbose by obtaining a list of all the pages to backup by parsing the base32768 ids from the backup dir tree.
        #Then we compare the modification date of _page.json to the modification date of the page itself.
        #If these timestamps are equivalent, then skip the backup of the page. Else, backup the page and set the modification date of _page.json to match Notion.
        #Calling the API that returns the list of recently visited pages will be useful, as else pages at level 2,4,etc will get downloaded anyway.

        pages = self.getPrivatePages()
        #print(json.dumps(pages, indent=4, ensure_ascii=False))

        pagesToDump = list(pages.keys())
        while True:
            hasDumpedPage = False

            for pageId in pagesToDump:
                if pageId in pages and "blocks" in pages[pageId]:
                    continue

                blocks = self.getPageBlocks(pageId, pages[pageId]["title"])
                for block in blocks:
                    if block["type"] == "page" and block["parent_id"] == pageId and block["alive"]:
                        pagesToDump.append(block["id"])
                        pages[block["id"]] = {
                            "id": block["id"],
                            "title": block["properties"]["title"][0][0],
                            "parentId": block["parent_id"] if block["parent_id"] != self.PRIVATE_SPACE_ID else None,
                            "ytVideoIds": [],
                            "ytPlaylistIds": [],
                            "createdTimestampMs": block["created_time"],
                            "lastEditedTimestampMs": block["last_edited_time"],
                        }

                #Easier to use regex than to parse whatever nested hell Notion's blocks are
                #We assume URLs are an entire string (which they are for the stuff I've checked), to not match the linked videos in the description
                for match in re.finditer(r"\"((?:https?:)?\/\/)?((?:www|m)\.)?((((?:youtube(?:-nocookie)?\.com))(\/(?:[\w\-]+\?v=|playlist\/?\?list=|v\/)))|(youtu\.be\/))(?P<id>[A-Za-z0-9_-]+)(\S+)?\"", json.dumps(blocks), re.IGNORECASE):
                    try:
                        id = match.groupdict()["id"]
                        if utils.isValidYtVideoId(id):
                            pages[pageId]["ytVideoIds"].append(id)
                        elif utils.isValidYtPlaylistId(id):
                            pages[pageId]["ytPlaylistIds"].append(id)
                        else:
                            raise ValueError("Invalid id '%s'" % (id))
                    except Exception as e:
                        print("Could not parse youtube url '%s': %s" % (match, e))
                        raise

                pages[pageId]["blocks"] = blocks
                hasDumpedPage = True

            if not hasDumpedPage:
                break


        #Assign depth and path to each page
        pageIds = list(pages.keys())
        sortedPageIds = []
        while True:
            needsResorting = False
            for pageId in pageIds:
                if pageId in sortedPageIds:
                    continue
                if pages[pageId]["parentId"] is None:
                    sortedPageIds.append(pageId)
                elif pages[pageId]["parentId"] in sortedPageIds:
                    sortedPageIds.append(pageId)
                else:
                    needsResorting = True
            if not needsResorting:
                break

        if len(sortedPageIds) != len(pageIds):
            raise ValueError("Page id sorting is buggy")

        for pageId in sortedPageIds:
            pages[pageId]["path"] = pages[pageId]["title"] if pages[pageId]["parentId"] is None else pages[pages[pageId]["parentId"]]["path"] + " > " + pages[pageId]["title"]
            pages[pageId]["depth"] = 0 if pages[pageId]["parentId"] is None else pages[pages[pageId]["parentId"]]["depth"] + 1

        self.backupPages(pages)


if __name__ == "__main__":
    notion = Notion()
    #print(blocks)

    #print("\n".join(sorted([p["title"] for p in pages.values()])))
