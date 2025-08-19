import json
import os
import re
import subprocess
import praw
import csv
from datetime import datetime
import time
from bs4 import BeautifulSoup
import requests
import config
import utils
import waybackmachine
import urllib.parse
from typing import cast

class Reddit():
    def __init__(self):

        with open("C:/Users/Zezombye/reddit.owo", "r") as f:
            self.redditCredentials = json.load(f)

        self.reddit = praw.Reddit(
            client_id=self.redditCredentials["clientId"],
            client_secret=self.redditCredentials["clientSecret"],
            user_agent="ZezSaveBot/1.0 (by u/Zezombye)",
            username="Zezombye",
            password=self.redditCredentials["zezPassword"]
        )
        
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

        self.waybackMachine = waybackmachine.WaybackMachine()


        os.makedirs(config.BACKUP_DIR+"reddit/css", exist_ok=True)
        os.makedirs(config.BACKUP_DIR+"reddit/js", exist_ok=True)
        os.makedirs(config.BACKUP_DIR+"reddit/img", exist_ok=True)
        os.makedirs(config.BACKUP_DIR+"reddit/videos", exist_ok=True)
        

    def get_saved_posts(self, limit=None):

        print("Getting saved posts from Reddit")

        saved_items = []
        
        # Get saved items (posts and comments)
        for item in self.reddit.user.me().saved(limit=limit): # type: ignore

            item_info = {
                "apiData": json.dumps(item.__dict__, default=str, indent=4, ensure_ascii=False).replace(">", "\\>").replace("<", "\\<"),
                'subreddit': "/r/"+str(item.subreddit),
                'created_utc': item.created_utc,
                'created_date': datetime.fromtimestamp(item.created_utc).strftime('%Y-%m-%d %H:%M:%S'),
                "over_18": item.over_18,
            }

            if hasattr(item, 'title'):  # It's a submission/post
                #print(len(saved_items), item.title)
                item_info['type'] = "self" if item.is_self else "img" if item.domain == "i.redd.it" else "video" if item.is_video else "gallery" if getattr(item, "is_gallery", None) else 'post'
                item_info['id'] = item.id
                item_info['title'] = item.title
                item_info['url'] = item.url
                item_info["permalink"] = f"https://old.reddit.com{item.permalink}"
                
            else:  # It's a comment
                item_info['type'] = 'comment'
                item_info['id'] = item.name
                item_info['title'] = item.link_title
                item_info['url'] = item.link_url
                item_info["permalink"] = f"https://old.reddit.com{item.permalink}?context=10000"
            
            saved_items.append(item_info)
        
        return saved_items


    def getImageRelativeUrl(self, img_url):
        img_url = img_url.replace("//preview.redd.it/", "//i.redd.it/")
        if not img_url.startswith("https://i.redd.it/"):
            raise ValueError("Invalid image URL: %s" % img_url)
        return "../img/" + utils.sanitizeForWindowsFilename(img_url.split("?")[0])


    def downloadImage(self, img_url):
        img_url = img_url.replace("//preview.redd.it/", "//i.redd.it/")
        if not img_url.startswith("https://i.redd.it/"):
            raise ValueError("Invalid image URL: %s" % img_url)
        
        img_filename = config.BACKUP_DIR+"reddit/img/" + utils.sanitizeForWindowsFilename(img_url.split("?")[0])
        if os.path.exists(img_filename):
            print("Image %s already exists, skipping" % (img_url))
            return
        
        print("Downloading image:", img_url)
        r = self.session.get(img_url)
        if not r.ok:
            raise Exception("Failed to download image %s: %s %s" % (img_url, r.status_code, r.text))
        
        with open(img_filename, "wb+") as img_file:
            img_file.write(r.content)


    def downloadPost(self, post):

        id = post["id"]
        title = post["title"]
        subredditDir = utils.sanitizeForWindowsFilename(post["subreddit"])
        os.makedirs(config.BACKUP_DIR+"reddit/"+subredditDir, exist_ok=True)
        filename = post["created_date"].split(" ")[0]+utils.SEPARATOR+ utils.sanitizeForWindowsFilename(title)[:200] + utils.SEPARATOR+id+ ".html"

        for file in os.listdir(config.BACKUP_DIR+"reddit/"+subredditDir):
            if file.endswith(utils.SEPARATOR+id+ ".html"):
                print("Post %s '%s' already exists, skipping" % (id, title))
                return

        self.waybackMachine.archiveUrl(post["permalink"])
        if post["type"] == "post":
            self.waybackMachine.archiveUrl(post["url"])

        print("Downloading %s %s" % (post["type"], post["permalink"]))
        r = self.session.post("https://old.reddit.com/over18", params={"dest": post["permalink"]}, data={"over18": "yes"}) if post["over_18"] else self.session.get(post["permalink"])
        if not r.ok:
            raise Exception("Failed to download post: %s" % (r.status_code, r.text))
        
        #Unquote because sometimes Reddit redirects to a URL with encoded characters
        #Eg: https://old.reddit.com/r/vosfinances/comments/1g1l6j3/éternel_retour_du_débat_dca_vs_lump_sum/lrhbt03/?context=10000
        if r.request.url != post["permalink"] and urllib.parse.unquote(cast(str, r.request.url)) != post["permalink"]:
            raise ValueError("Redirected to '%s', expected '%s'" % (r.request.url, post["permalink"]))
        
        with open("debug/reddit_post.html", "w+", encoding="utf-8") as f:
            f.write(r.text)


        # Save all css stylesheets
        soup = BeautifulSoup(r.text, 'html.parser')
        stylesheets = soup.find_all('link', rel='stylesheet', href=True)
        for stylesheet in stylesheets:
            if stylesheet.get("ref") == "applied_subreddit_stylesheet":
                #Remove subreddit stylesheets as they mostly suck
                stylesheet.decompose()
                continue
            href = stylesheet.get('href')
            if href.startswith('//'):
                href = 'https:' + href
            elif href.startswith('/'):
                href = 'https://old.reddit.com' + href

            stylesheet['href'] = "../css/"+utils.sanitizeForWindowsFilename(href)

            css_filename = config.BACKUP_DIR+"reddit/css/" + utils.sanitizeForWindowsFilename(href)

            if os.path.exists(css_filename):
                #print("Stylesheet %s already exists, skipping" % (href))
                continue

            print("Downloading stylesheet:", href)
            
            r = self.session.get(href)
            if not r.ok:
                raise Exception("Failed to download stylesheet %s: %s" % (href, r.status_code, r.text))
            with open(css_filename, "w+", encoding="utf-8", newline="\n") as css_file:
                css_file.write(r.text)

        # Save all javascript files
        scripts = soup.find_all('script', src=True)
        for script in scripts:
            src = script.get('src')
            if not src:
                continue
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                src = 'https://old.reddit.com' + src

            script['src'] = "../js/"+utils.sanitizeForWindowsFilename(src)

            js_filename = config.BACKUP_DIR+"reddit/js/" + utils.sanitizeForWindowsFilename(src)

            if os.path.exists(js_filename):
                #print("Script %s already exists, skipping" % (src))
                continue

            print("Downloading script:", src)
            
            r = self.session.get(src)
            if not r.ok:
                raise Exception("Failed to download script %s: %s" % (src, r.status_code, r.text))
            with open(js_filename, "w+", encoding="utf-8", newline="\n") as js_file:
                js_file.write(r.text)


        if post["type"] == "gallery":
            if not post["url"].startswith("https://www.reddit.com/gallery/"):
                raise ValueError("Gallery post URL is not valid: '%s'" % post["url"])
            # Save gallery images
            galleryImages = soup.find_all("a", class_="gallery-item-thumbnail-link")
            for img in galleryImages:
                img_url = img.get('href')
                if not img_url or not img_url.startswith('https://preview.redd.it/'):
                    raise ValueError("Invalid image URL in gallery: %s" % img_url)
                
                self.downloadImage(img_url)


        elif post["type"] == "img":
            if not post["url"].startswith("https://i.redd.it/"):
                raise ValueError("Image post URL is not valid: '%s'" % post["url"])
            # Save single image
            img_url = post["url"]
            self.downloadImage(img_url)



        elif post["type"] == "video":
            if not post["url"].startswith("https://v.redd.it/"):
                raise ValueError("Video post URL is not valid: '%s'" % post["url"])
            
            videoId = post["url"].split("?")[0].split("/")[-1]
            videoFilename = config.BACKUP_DIR+"reddit/videos/" + videoId+ ".mp4"
            if not os.path.exists(videoFilename):
                print("Downloading video:", post["url"])
                subprocess.check_output(["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]", "-o", videoFilename, post["url"]], stderr=subprocess.STDOUT)

            inlineVideoTag = soup.find("div", class_="media-preview-content video-player")
            if not inlineVideoTag:
                raise ValueError("No video tag found in post")
            
            inlineVideoTag.clear() # type: ignore
            inlineVideoTag.append(soup.new_tag("video", controls="true", style="max-width: 600px; max-height: 486px;", src="../videos/" + videoId + ".mp4"))

        elif post["type"] in ["comment", "self", "post"]:
            pass

        else:
            raise ValueError("Unsupported post type: %s" % post["type"])


        # Download and replace inline images
        inline_images = soup.find_all("a", href=True)
        for img in inline_images:
            href = img.get('href')
            if not href or not href.startswith('https://preview.redd.it/') or img.string != "<image>":
                continue

            # Convert link to img tag
            img_tag = soup.new_tag("img", style="max-width: 400px; max-height: 400px;", src=self.getImageRelativeUrl(href))
            img.replace_with(img_tag)
            self.downloadImage(href)

        # Fix relative image links
        preview_images = soup.find_all("img", src=True)
        for img in preview_images:
            src = img.get('src').replace("//preview.redd.it/", "//i.redd.it/")
            if src.startswith('//'):
                img["src"] = 'https:' + src
            if (post["type"] in ["gallery", "img"]) and src.startswith('https://i.redd.it/'):
                img['src'] = "../img/" + utils.sanitizeForWindowsFilename(src.split("?")[0])

        # Fix relative links
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href')
            if href.startswith('/'):
                href = 'https://old.reddit.com' + href
                link['href'] = href
        

        soup.find("head").append(soup.new_tag("link", rel="stylesheet", href="../css/_additional-styles.css")) # pyright: ignore[reportOptionalMemberAccess]
        with open(config.BACKUP_DIR+"reddit/"+subredditDir+"/"+filename, "w+", encoding="utf-8", newline="\n") as file:
            file.write("<!--\n"+post["apiData"]+"\n-->\n"+soup.prettify())

        time.sleep(5)


if __name__ == "__main__":
    reddit = Reddit()
    saved_items = reddit.get_saved_posts()
    for i, saved_item in enumerate(saved_items):
        reddit.downloadPost(saved_item)
