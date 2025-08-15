#!/usr/bin/python3
import os, json

BACKUP_DIR = "D:/bkp/"

WL_ID = "PLK5yrmOBPizjuP7IUTU3HcCo3YJ3L96Dz" #I guess useful in case I want to sort it or something

#Those playlists will be sorted according to song hash (except if in ytMusicPlaylistsToNotSort), and checked for unavailable videos as well as duplicates
ytMusicPlaylists = [
    "PLDS8MSVtwiPYVvz3D43_gWJGfXKv8ZTxg", #Best of music
    "PLDS8MSVtwiPZ0QHhxgNaoAPCTgXL4aYfQ", #Best of albums
    "PLDS8MSVtwiPZMhCA6ABpJCVBWCY4WcKw3", #Ballads & soft songs
    "PLDS8MSVtwiPZ53t18Oae17V71yCPffK9r", #Romantic mixtape
]
ytMusicPlaylistsToNotSort = [
    "PLDS8MSVtwiPZ53t18Oae17V71yCPffK9r", #Romantic mixtape
]

#Will only download the audio for these playlists, and try to fix missing songs
ytMusicPlaylistsToDownload = [
    "PLDS8MSVtwiPYVvz3D43_gWJGfXKv8ZTxg", #Best of music
    "PLDS8MSVtwiPZMhCA6ABpJCVBWCY4WcKw3", #Ballads & soft songs
    "PLDS8MSVtwiPb-BwwJ7_krnU-O-yUH7uTA", #War mixtape
    "PLDS8MSVtwiPZ53t18Oae17V71yCPffK9r", #Romantic mixtape
    "PLDS8MSVtwiPZ0QHhxgNaoAPCTgXL4aYfQ", #Best of albums
]

ytPlaylistsToDownload = [
    "PLDS8MSVtwiPYL6t48oRBhi53xqG3UBArU", #Tate motivation/insights
    "PLDS8MSVtwiPYFV57YlnPG1gpnH6u8Q-yX", #Good shit
    "PLDS8MSVtwiPbbkFXiGIxZAIO1_XQXt60g", #Music shitposts
	"PLDS8MSVtwiPZT37BUdFbO07glh7ZXZqxY", #Relationships
    "PLDS8MSVtwiPYsuGaK8pGFmuF8gLK_yV4c", #Parenting
    "PLDS8MSVtwiPbAJS4KbhIL0DEjEZoJVIMb", #Chess
    "PLDS8MSVtwiPYCue38uxLKjuZ59f3Gc-DE", #Motivation
    "PLDS8MSVtwiPbWERtwPmAi_esGDOioV2c3", #Social skills
    "PLDS8MSVtwiPZTUdYnf8KQSWECqZ6EgAJn", #Boxing/MMA
    "PLDS8MSVtwiPa-PmpT3aWGRyagMY3s-QE6", #MBTI/INTJ
    "PLDS8MSVtwiPaBCQg5iwtMJzbxz7KYjTuw", #Graphic/web design
    "PLDS8MSVtwiPYS0o6qCLC6UBOkagU4Jmn1", #Fitness
]
