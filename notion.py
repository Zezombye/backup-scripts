#!/usr/bin/python3

import os
import json
import shutil
import time
import unicodedata
import re
import base32768
import utils

import requests

class Notion():

    def __init__(self):
        self.notionTokenFile = "C:/Users/Zezombye/notion.owo"
        self.notionCookieFile = "C:/Users/Zezombye/notion_cookie.owo"

        with open("notion_settings.json", "r") as f:
            notionSettings = json.loads(f.read())

        self.PRIVATE_SPACE_ID = notionSettings["privateSpaceId"]
        self.backupDir = "D:/bkp/no/"

        with open(self.notionTokenFile, "r") as f:
            self.notionToken = f.read().strip()
        with open(self.notionCookieFile, "r") as f:
            self.notionCookie = f.read().strip()

        self.session = requests.session()
        self.session.headers = {"Cookie": self.notionCookie, **notionSettings["headers"]}


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
            }

        return pages

    def getPageBlocks(self, pageId):
        print("Getting page blocks of '%s'" % (pageId))

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

            blocks.extend([b["value"]["value"] for b in r["recordMap"]["block"].values() if b["value"]["value"]["id"] not in [b2["id"] for b2 in blocks]])

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

            targetDir = os.path.join(self.backupDir, pagePath)

            # Check if any directories end with the specific identifier
            for root, dirs, _ in os.walk(self.backupDir):
                for dirName in dirs:
                    dirPath = os.path.join(root, dirName).replace("\\", "/")
                    # Check if the directory ends with the required identifier
                    if dirName.endswith(utils.SEPARATOR + utils.guidToBase32768(pageId)) and dirPath != targetDir:

                        print("Page at '%s' has moved or been renamed, moving it to '%s'" % (dirPath, targetDir))

                        shutil.move(dirPath, targetDir)


            if not os.path.exists(targetDir):
                print("Creating directory '%s' for page id '%s'" % (targetDir, pageId))
            os.makedirs(targetDir, exist_ok=True)







if __name__ == "__main__":
    notion = Notion()

    #base64.urlsafe_b64decode("PLDS8MSVtwiPYFV57YlnPG1gpnH6u8Q-yX==")

    pages = notion.getPrivatePages()
    print(json.dumps(pages, indent=4, ensure_ascii=False))

    pagesToDump = list(pages.keys())
    while True:
        hasDumpedPage = False

        for page in pagesToDump:
            if page in pages and "blocks" in pages[page]:
                continue
            else:
                #blocks = notion.getPageBlocks(page)
                #for block in blocks:
                #    if block["type"] == "page" and block["parent_id"] == page:
                #        pagesToDump.append(block["id"])
                #        pages[block["id"]] = {
                #            "id": block["id"],
                #            "title": block["properties"]["title"][0][0],
                #            "parentId": block["parent_id"] if block["parent_id"] != self.PRIVATE_SPACE_ID else None,
                #        }
                #pages[page]["blocks"] = blocks
                pages[page]["blocks"] = []
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

    notion.backupPages(pages)

    #blocks = notion.getPageBlocks("2cb3169b-e81d-4404-9552-8afdef34a062")
    #print(blocks)

    #print("\n".join(sorted([p["title"] for p in pages.values()])))
