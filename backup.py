#!/usr/bin/python3

import json, os, sys
import youtube
import notion
import config

#Does all the daily tasks

youtube = youtube.Youtube()
notion = notion.Notion()

def sortMusicPlaylists():

    print("Sorting music playlists...")

    #Todo: handle the fact that songs in the romantic/ballads playlists should also be in the best of playlist.
    #The romantic playlist should not be sorted, but both should be checked for duplicates.
    #Most notably, if a song becomes unavailable in those playlists, and a video with the same song hash exists in the best of playlist, that video should be added to that playlist (with the same position) and the unavailable video should be removed.
    #Plus, if the song hash of a song in a child playlist matches a song in the parent playlist, but the videos are different, the video in the child playlist should be replaced.
    #Lastly, if a song in a parent playlist is removed, it should be removed from the child playlists.
    #This ensures I only have one playlist to truly maintain.

    for playlistId in config.ytMusicPlaylists:
        playlistInfo = youtube.get_playlist_info(playlistId)
        print("Sorting playlist '%s' (%s)" % (playlistId, playlistInfo["title"]))

        videos = youtube.get_playlist_videos(playlistId)

        songHashes = set()
        duplicatedSongHashes = set()
        for video in videos:
            if video["songHash"] in songHashes:
                duplicatedSongHashes.add(video["songHash"])
            else:
                songHashes.add(video["songHash"])

        for video in videos:
            if not video["isAvailable"]:
                if video["songHash"] in duplicatedSongHashes:
                    print("Video %s (%s) is no longer available but is a duplicate, removing it" % (video["id"], video["title"]))
                    youtube.delete_playlist_item(video["playlistitem_id"])
                    videos = [v for v in videos if v["id"] != video["id"]]
                elif video["title"] in ["Deleted video", "Privated video"]:
                    print("Video %s (%s) is no longer available, removing it" % (video["id"], video["title"]))
                    youtube.delete_playlist_item(video["playlistitem_id"])
                    videos = [v for v in videos if v["id"] != video["id"]]
                else:
                    print("Video %s (%s) is no longer available, put it again in the playlist for it to be removed" % (video["id"], video["title"]))


        uniqueVideos = {}
        for video in videos:
            videoHash = video["songHash"]
            if videoHash in uniqueVideos:
                print("Duplicate detected: video at pos %s with id %s '%s' is the same as video at pos %s with id %s '%s'" % (video["position"], video["id"], video["title"], uniqueVideos[videoHash]["position"], uniqueVideos[videoHash]["id"], uniqueVideos[videoHash]["title"]))
                #If the position is low, then it is a song I recently added and thus should be removed as there would be no meaningful difference (eg live/studio)
                if uniqueVideos[videoHash]["position"] < 20 and uniqueVideos[videoHash]["position"] < video["position"]:
                    print("Removing video %s" % (uniqueVideos[videoHash]["id"]))
                    youtube.delete_playlist_item(uniqueVideos[videoHash]["playlistitem_id"])
                    videos = [v for v in videos if v["id"] != uniqueVideos[videoHash]["id"]]
                elif video["position"] < 20 and video["position"] < uniqueVideos[videoHash]["position"]:
                    print("Removing video %s" % (video["id"]))
                    youtube.delete_playlist_item(video["playlistitem_id"])
                    videos = [v for v in videos if v["id"] != video["id"]]


            else:
                uniqueVideos[videoHash] = video


        artistCounts = {}
        for video in videos:
            artist = video["songHash"].split(" - ")[0]
            if artist in artistCounts:
                artistCounts[artist] += 1
            else:
                artistCounts[artist] = 1

        artistCounts = {k: v for k, v in sorted(artistCounts.items(), key=lambda item: -item[1])}
        #for artist, artistCount in artistCounts.items():
        #    print(artist, artistCount)

        videos = youtube.sort_playlist(playlistId, videos)

        #for video in videos:
        #    print(video["position"], self.getSongHash(video))


        with open("yt_playlists/"+youtube.normalize(playlistInfo["title"]).replace(" ", "_")+".json", "w+", encoding="utf-8") as f:
            f.write(json.dumps([{
                "title": v["title"],
                #"description": v["description"],
                "channelName": v["channelName"],
                "channelId": v["channelId"],
                "id": v["id"],
                "publishedAt": v["publishedAt"],
                "songHash": v["songHash"],
            } for v in videos], indent=4, ensure_ascii=False))


def backupYtPlaylists():
    print("Backing up playlists...")
    for playlistId in config.ytPlaylistsToDownload:
        youtube.download_playlist(playlistId)

    for playlistId in config.ytMusicPlaylistsToDownload:
        youtube.download_playlist(playlistId, audioOnly=True)


def backupNotion():
    print("Backing up Notion...")
    notion.backupAllPages()


sortMusicPlaylists()
backupYtPlaylists()
backupNotion()

print("Done")
