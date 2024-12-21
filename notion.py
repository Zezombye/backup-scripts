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
        self.USER_ID = notionSettings["userId"]
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

    def getPages(self):
        r = self.make_request("post", "https://www.notion.so/api/v3/getRecentPageVisits", {
            "limit": 9999,
            "spaceId": self.PRIVATE_SPACE_ID,
            "userId": self.USER_ID,
        })

        pages = {}

        #Some sort of intermediary page...?
        #Have to take it into account to get the actual parents
        transclusionContainers = []

        #Apparently when you move a page to trash it doesn't move all children to trash...
        #And some bug caused a deep, deep recursion
        #Mark the ids of the pages moved to trash, as well as their children
        #Also some weird template pages
        deletedPageIds = [
            "5213bbd3-c9a4-42d9-87d0-9dbf9e7025b2",
            "d089a334-6150-405f-9a56-0e29ea172e10",
            "5464121f-63f6-43ae-bbc8-4a5d861b8e22",
            "307f4705-dab2-4cb6-8367-0c0310934be1",
            "c19f2b71-de92-4d3c-9461-185dc3097f0d",
            "18d422d2-3e7c-467f-9433-08b4a745482e",
            "a8f93a94-6a94-4fdb-ba14-38d52f2c3396",
            "3686fc2f-816a-4cce-a25e-253f571c1a0c",
        ]

        for block in r["recordMap"]["block"].values():
            if "value" not in block["value"]:
                continue
            block = block["value"]["value"]
            #print(block["id"])
            if block["type"] == "transclusion_container":
                transclusionContainers.append(block)
            if block["type"] != "page" or "properties" not in block or "title" not in block["properties"] or block.get("is_template"):
                continue

            if not block["alive"] or block.get("moved_to_trash_id"):
                deletedPageIds.append(block["id"])
                continue

            if block["parent_table"] == "collection":
                #We don't care about dummy pages made for todo lists. No important info should be in there anyway
                continue

            if block["parent_table"] not in ["space", "block"]:
                raise ValueError("Unhandled parent_table '%s' for page '%s'" % (block["parent_table"], block["id"]))


            pages[block["id"]] = {
                "id": block["id"],
                "title": block["properties"]["title"][0][0],
                "parentId": None if block["parent_id"] == self.PRIVATE_SPACE_ID else block["parent_id"],
                "ytVideoIds": [],
                "ytPlaylistIds": [],
                "createdTimestamp": int(block["created_time"]/1000),
                "lastEditedTimestamp": int(block["last_edited_time"]/1000),
            }

        #Sanity check in case Notion secretly changes the api or decreases the limit
        if len(pages.keys()) < 165:
            raise ValueError("Could not get all pages: only got %s" % (len(pages.keys())))

        #Fix parents
        for tc in transclusionContainers:
            for pageId in tc["content"]:
                pages[pageId]["parentId"] = tc["parent_id"]

        #Fix children of deleted pages
        while True:
            hasMarkedPageAsDeleted = False
            for pageId in list(pages.keys()):
                if pages[pageId]["parentId"] in deletedPageIds or pageId in deletedPageIds:
                    deletedPageIds.append(pageId)
                    del pages[pageId]
                    hasMarkedPageAsDeleted = True

            if not hasMarkedPageAsDeleted:
                break

        return pages

    def getPageBlocks(self, pageId, pageTitle):
        #print("Getting page blocks of '%s' (%s)" % (pageId, pageTitle))

        blocks = []
        cursorStack = []
        while True:
            r = self.make_request("post", "https://www.notion.so/api/v3/loadPageChunkV2", {
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

        pageIds = sorted(list(pages.keys()), key=lambda x: (pages[x]["depth"], pages[x]["displayPath"]))

        for pageId in pageIds:
            if pages[pageId]["skipBackup"]:
                continue
            print("Backing up page %s ('%s')" % (pageId, pages[pageId]["displayPath"]))
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

            os.utime(targetDir+"/_page.json", (pages[pageId]["lastEditedTimestamp"], pages[pageId]["lastEditedTimestamp"]))

            pages[pageId]["ytVideoIds"] = list(set(pages[pageId]["ytVideoIds"]))
            for ytVideoId in pages[pageId]["ytVideoIds"]:
                print("Downloading yt video '%s'" % (ytVideoId))
                self.youtube.download_video(ytVideoId, targetDir)

            pages[pageId]["ytPlaylistIds"] = list(set(pages[pageId]["ytPlaylistIds"]))
            for ytPlaylistId in pages[pageId]["ytPlaylistIds"]:
                print("Downloading yt playlist '%s'" % (ytPlaylistId))
                self.youtube.download_playlist(ytPlaylistId, targetDir)


    def backupAllPages(self):

        pages = self.getPages()
        #print(json.dumps(pages, indent=4, ensure_ascii=False))

        #We can speed up the process and make the logs less verbose by comparing the modification date of _page.json to the modification date of the page itself.
        #If these timestamps are equivalent, then skip the backup of the page. Else, backup the page and set the modification date of _page.json to match Notion.
        for pageId in pages:
            pageJsonPath = os.path.join(self.BACKUP_DIR, self.getPagePath(pages, pageId), "_page.json")
            if os.path.exists(pageJsonPath) and int(os.path.getmtime(pageJsonPath)) == pages[pageId]["lastEditedTimestamp"]:
                pages[pageId]["skipBackup"] = True
            else:
                pages[pageId]["skipBackup"] = False


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
            pages[pageId]["displayPath"] = pages[pageId]["title"] if pages[pageId]["parentId"] is None else pages[pages[pageId]["parentId"]]["displayPath"] + " > " + pages[pageId]["title"]
            pages[pageId]["depth"] = 0 if pages[pageId]["parentId"] is None else pages[pages[pageId]["parentId"]]["depth"] + 1


        #Get content of each page
        for pageId in sortedPageIds:
            if pages[pageId]["skipBackup"]:
                #print("Skipping backup of %s (%s), not modified" % (pageId, pages[pageId]["displayPath"]))
                continue

            blocks = self.getPageBlocks(pageId, pages[pageId]["displayPath"])

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



        self.backupPages(pages)


if __name__ == "__main__":
    notion = Notion()
    #print(blocks)

    #print("\n".join(sorted([p["title"] for p in pages.values()])))
