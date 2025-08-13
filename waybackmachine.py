import json
import re
import time
import datetime
from typing import Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from requests.models import Response
from requests.structures import CaseInsensitiveDict
from urllib3.util.retry import Retry

#https://github.com/akamhy/waybackpy/blob/master/waybackpy/save_api.py

class WaybackMachine:
    def __init__(self) -> None:
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})


    def isUrlArchived(self, url):
        r = self.session.get("https://archive.org/wayback/available", params={"url": url})
        if not r.ok:
            raise Exception("Failed to check if URL '%s' is archived. Status code: %s, %s" % (url, r.status_code, r.text))
        
        availabilityData = r.json()
        with open("debug/archiveorg_available.json", "w+", encoding="utf-8") as f:
            f.write(json.dumps(availabilityData, indent=4, ensure_ascii=False))
        
        return bool(availabilityData["archived_snapshots"])


    def archiveUrl(self, url):

        print("Checking if URL '%s' is already archived..." % url)
        if self.isUrlArchived(url):
            return

        print("Requesting Wayback Machine to save URL: %s" % url)
        r = self.session.post("https://web.archive.org/save/"+url, data={"url": url, "capture_all": "on"})

        print("Response: %s" % (r.status_code))
        with open("debug/archiveorg_save.html", "w+", encoding="utf-8") as f:
            f.write(r.text)

        if not r.ok:
            raise Exception("Failed to save URL '%s' to Wayback Machine. Status code: %s" % (url, r.status_code))
        
        if re.search(r'<p>The capture will start in ~\d+ hours? because our service is currently overloaded. You may close your browser window and the page will still be saved.</p>', r.text):
            print("Wayback Machine is overloaded, capture will start in a few hours.")
            return

        pollUrl = re.search(r'spn\.watchJob\("spn2-([0-9a-f]+)",', r.text)
        if not pollUrl:
            raise Exception("Failed to find poll URL in response for '%s'" % (url))
        pollUrl = "https://web.archive.org/save/status/spn2-"+pollUrl.group(1)

        print("Poll URL: %s" % (pollUrl))

        tries = 0
        while True:
            r = self.session.get(pollUrl+"?_t="+str(int(time.time()*1000)))
            if not r.ok:
                if r.status_code == 404:
                    #Sometimes occur, but the url should be archived
                    time.sleep(6)
                    if self.isUrlArchived(url):
                        print("URL '%s' is archived despite 404 error during polling." % url)
                        return
                raise Exception("Failed to poll Wayback Machine for '%s'. Status code: %s, %s" % (url, r.status_code, r.text))
            
            pollStatus = r.json()
            if pollStatus["status"] == "pending":
                if tries > 100: #10mn
                    raise Exception("Wayback Machine is taking too long to save '%s': %s" % (url, pollStatus))
                print("Pending... %s resources archived" % (len(pollStatus["resources"])))
                tries += 1
                time.sleep(6)
                continue
            elif pollStatus["status"] == "success":
                #print(pollStatus)
                print("Successfully saved at https://web.archive.org/web/%s/%s" % (pollStatus["timestamp"], url))
                return
            else:
                raise Exception("Failed to save '%s' to Wayback Machine: %s" % (url, pollStatus))
    
            
if __name__ == "__main__":
    url = "https://old.reddit.com/r/ENFP/comments/1j5h0wg/enfp_m_this_is_my_experience/"
    wayback = WaybackMachine()
    wayback.archiveUrl(url)
