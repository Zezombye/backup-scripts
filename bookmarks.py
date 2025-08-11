#!/usr/bin/python3

import os
import sys
import json
import sqlite3
import re
import utils

class Bookmarks:

    def __init__(self):
        self.TYPE_LINK = 1
        self.TYPE_FOLDER = 2

    def getBookmarks(self):
        #Load bookmarks from Firefox
        bookmarks_file = "C:/Users/Zezombye/AppData/Roaming/Mozilla/Firefox/Profiles/r530li2w.default/places.sqlite"
        
        if not os.path.exists(bookmarks_file):
            print("Bookmarks file not found.")
            return []
        
        conn = sqlite3.connect(bookmarks_file)
        cursor = conn.cursor()

        cursor.execute("""
            select mb.id, mb.parent, mb.guid, mb.type, mb.title, mp.url from moz_bookmarks mb
            left join moz_places mp on mp.id = mb.fk
            where mb.type in (1, 2)
            order by mb.id
        """)

        bookmarks = []
        for row in cursor.fetchall():
            bookmark = {
                "id": row[0],
                "parent": row[1],
                "guid": row[2],
                "type": row[3],
                "title": row[4],
                "url": row[5],
                "children": []
            }
            bookmarks.append(bookmark)

        conn.close()

        bookmark_map = {bookmark['id']: bookmark for bookmark in bookmarks}
    
        # List to store root-level bookmarks (those with no parent or parent not found)
        root_bookmarks = []
        
        # Build the tree by assigning children to their parents
        for bookmark in bookmarks:
            parent_id = bookmark['parent']
            
            # If bookmark has no parent or parent doesn't exist, it's a root bookmark
            if parent_id is None or parent_id not in bookmark_map:
                if bookmark["guid"] != "root________":
                    raise ValueError(f"Bookmark '{bookmark['title']} with id {bookmark['id']} has an invalid parent id: {parent_id}")
                root_bookmarks.append(bookmark)
            else:
                # Add this bookmark as a child of its parent
                parent_bookmark = bookmark_map[parent_id]
                parent_bookmark['children'].append(bookmark)

        toolbarBookmark = [b for b in bookmarks if b['guid'] == 'toolbar_____']
        if len(toolbarBookmark) != 1:
            raise ValueError("Could not find exactly one toolbar bookmark")
        toolbarBookmark = toolbarBookmark[0]
        
        return toolbarBookmark['children']

    def bookmarksToMarkdown(self, bookmarks, depth=0):
        result = ""
        bookmarks = sorted(bookmarks, key=lambda x: ("a" if x["type"] == self.TYPE_FOLDER else "b") + x['title'].lower())
        if depth == 0:
            otherBookmarks = [b for b in bookmarks if b['type'] == self.TYPE_LINK]
            bookmarks = [b for b in bookmarks if b['type'] == self.TYPE_FOLDER]
            if len(otherBookmarks) > 0:
                bookmarks.append({
                    "title": "Other",
                    "type": self.TYPE_FOLDER,
                    "children": otherBookmarks
                })

        for bookmark in bookmarks:
            sanitizedTitle = utils.sanitizeForMarkdown(bookmark['title']).strip()
            # Remove "- website title" suffix if it exists
            sanitizedTitle = sanitizedTitle.rsplit(" - ", 1)[0] if " - " in sanitizedTitle else sanitizedTitle
            sanitizedTitle = sanitizedTitle.rsplit(" | ", 1)[0] if " | " in sanitizedTitle else sanitizedTitle
            sanitizedTitle = sanitizedTitle.rsplit(" ― ", 1)[0] if " ― " in sanitizedTitle else sanitizedTitle
            sanitizedTitle = sanitizedTitle.rsplit(" — ", 1)[0] if " — " in sanitizedTitle else sanitizedTitle


            if bookmark['type'] == self.TYPE_LINK:
                sanitizedUrl = utils.sanitizeForMarkdown(bookmark['url'])
                urlDomain = re.sub(r'^https?://(www\.)?', '', bookmark["url"]).split('/')[0] if sanitizedUrl else ""

                result += "  " * depth + f"- [{sanitizedTitle}]({sanitizedUrl}) [{urlDomain}]\n"
            elif bookmark['type'] == self.TYPE_FOLDER:
                result += "  " * depth + f"- **{sanitizedTitle}**\n"
                if 'children' in bookmark and bookmark['children']:
                    result += self.bookmarksToMarkdown(bookmark['children'], depth + 1)
        return result
    

if __name__ == "__main__":
    bookmarks = Bookmarks()
    bookmarkTree = bookmarks.getBookmarks()
    print(bookmarks.bookmarksToMarkdown(bookmarkTree))
