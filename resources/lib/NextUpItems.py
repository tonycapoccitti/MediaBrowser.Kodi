#################################################################################################
# NextUp TV Updater
#################################################################################################

import xbmc
import xbmcgui
import xbmcaddon

import json
import threading
from datetime import datetime
import urllib
from DownloadUtils import DownloadUtils
from Database import Database
_MODE_BASICPLAY=12

#define our global download utils
downloadUtils = DownloadUtils()
db = Database()

class NextUpUpdaterThread(threading.Thread):

    logLevel = 0
    event = None
    exit = False    
    
    def __init__(self, *args):
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        level = addonSettings.getSetting('logLevel')        
        self.logLevel = 0
        if(level != None):
            self.logLevel = int(level)           
    
        xbmc.log("XBMB3C NextUpUpdaterThread -> Log Level:" +  str(self.logLevel))
        
        self.event =  threading.Event()
        
        threading.Thread.__init__(self, *args)    
    
    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("XBMB3C NextUpUpdaterThread -> " + msg)
        
    def stop(self):
        self.logMsg("stop called")
        self.exit = True
        self.event.set()
        
    def run(self):
        self.logMsg("Started")
        
        self.updateNextUp()
        lastRun = datetime.today()
        
        while (xbmc.abortRequested == False and self.exit != True):
            td = datetime.today() - lastRun
            secTotal = td.seconds
            
            if(secTotal > 300):
                self.updateNextUp()
                lastRun = datetime.today()

            self.logMsg("entering event wait")
            self.event.wait(30.0)
            self.logMsg("event wait finished")
                        
        self.logMsg("Exited")
        
    def updateNextUp(self):
        self.logMsg("updateNextUp Called")
        useBackgroundData = xbmcgui.Window(10000).getProperty("BackgroundDataLoaded") == "true"
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        
        mb3Host = addonSettings.getSetting('ipaddress')
        mb3Port = addonSettings.getSetting('port')    
        userName = addonSettings.getSetting('username')     
        
        userid = downloadUtils.getUserId()
        self.logMsg("updateNextUp UserID : " + userid)
        
        self.logMsg("Updating NextUp List")
        
        nextUpUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Shows/NextUp?UserId=" + userid + "&Fields=Path,Genres,MediaStreams,Overview,ShortOverview&format=json&ImageTypeLimit=1"
        
        jsonData = downloadUtils.downloadUrl(nextUpUrl, suppress=True, popup=1 )
        if(jsonData == ""):
            return
            
        result = json.loads(jsonData)
        self.logMsg("NextUP TV Show Json Data : " + str(result), level=2)
        
        result = result.get("Items")
        WINDOW = xbmcgui.Window( 10000 )
        if(result == None):
            result = []   

        item_count = 1
        for item in result:
            title = "Missing Title"
            if(item.get("Name") != None):
                title = item.get("Name").encode('utf-8')
                
            seriesName = "Missing Name"
            if(item.get("SeriesName") != None):
                seriesName = item.get("SeriesName").encode('utf-8')   

            eppNumber = "X"
            tempEpisodeNumber = "XX"
            if(item.get("IndexNumber") != None):
                eppNumber = item.get("IndexNumber")
                if eppNumber < 10:
                  tempEpisodeNumber = "0" + str(eppNumber)
                else:
                  tempEpisodeNumber = str(eppNumber)
            
            seasonNumber = item.get("ParentIndexNumber")
            tempSeasonNumber = "XX"
            if seasonNumber < 10:
              tempSeasonNumber = "0" + str(seasonNumber)
            else:
              tempSeasonNumber = str(seasonNumber)
            rating = str(item.get("CommunityRating"))
            plot = item.get("Overview")
            if plot == None:
                plot=''
            plot=plot.encode('utf-8')
            shortplot = item.get("ShortOverview")
            if shortplot == None:
                shortplot = ''
            shortplot = shortplot.encode('utf-8')
            year = item.get("ProductionYear")
            item_id = item.get("Id")
            seriesId = item.get("SeriesId")
            
            if useBackgroundData != True:
                seriesJsonData = downloadUtils.downloadUrl("http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items/" + seriesId + "?format=json", suppress=True, popup=1 )
                seriesResult = json.loads(seriesJsonData)      
                officialrating = seriesResult.get("OfficialRating")        
                poster = downloadUtils.getArtwork(seriesResult, "Primary3")
                small_poster = downloadUtils.getArtwork(seriesResult, "Primary2")
                thumbnail = downloadUtils.getArtwork(item, "Primary")
                logo = downloadUtils.getArtwork(seriesResult, "Logo")
                fanart = downloadUtils.getArtwork(item, "Backdrop")
                medium_fanart = downloadUtils.getArtwork(item, "Backdrop3")
                banner = downloadUtils.getArtwork(item, "Banner")
                if (seriesResult.get("ImageTags") != None and seriesResult.get("ImageTags").get("Thumb") != None):
                  seriesthumbnail = downloadUtils.getArtwork(seriesResult, "Thumb3")
                else:
                  seriesthumbnail = fanart 
            else:
                # get rid of the call below when we can get the series userdata
                officialrating = db.get(seriesId + ".OfficialRating")
                poster = db.get(seriesId +  ".Primary3")
                small_poster = db.get(seriesId +  ".Primary2")
                thumbnail = db.get(seriesId +  ".Primary")
                logo = db.get(seriesId + ".Logo")
                fanart = db.get(seriesId + ".Backdrop")
                medium_fanart = db.get(seriesId + ".Backdrop3")
                banner = db.get(seriesId + ".Banner")
                if (item.get("SeriesThumbImageTag") != None and item.get("SeriesThumbImageTag") != ""):
                  seriesthumbnail = db.get(seriesId +  ".Thumb3")
                else:
                  seriesthumbnail = fanart
                                  
            url =  mb3Host + ":" + mb3Port + ',;' + item_id
            playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
            playUrl = playUrl.replace("\\\\","smb://")
            playUrl = playUrl.replace("\\","/")    

            # Process UserData
            userData = item.get("UserData")
            if(userData != None):
                resume = str(userData.get("PlaybackPositionTicks"))
                if (resume == "0"):
                    resume = "False"
                else:
                    resume = "True"

            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".EpisodeTitle = " + title, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".ShowTitle = " + seriesName, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".EpisodeNo = " + tempEpisodeNumber, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".SeasonNo = " + tempSeasonNumber, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".Thumb = " + thumbnail, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".Path  = " + playUrl, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".Rating  = " + rating, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".Art(tvshow.fanart)  = " + fanart, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".Art(tvshow.clearlogo)  = " + logo, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".Art(tvshow.banner)  = " + banner, level=2)  
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".Art(tvshow.poster)  = " + poster, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".Plot  = " + plot, level=2)
            self.logMsg("NextUpEpisodeMB3." + str(item_count) + ".Resume  = " + resume, level=2)
            
            
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".EpisodeTitle", title)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".ShowTitle", seriesName)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".EpisodeNo", tempEpisodeNumber)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".SeasonNo", tempSeasonNumber)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".Thumb", thumbnail)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".SeriesThumb", seriesthumbnail)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".Path", playUrl)            
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".Rating", rating)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".Art(tvshow.fanart)", fanart)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".Art(tvshow.medium_fanart)", medium_fanart)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".Art(tvshow.clearlogo)", logo)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".Art(tvshow.banner)", banner)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".Art(tvshow.poster)", poster)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".Art(tvshow.small_poster)", small_poster)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".Plot", plot)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".ShortPlot", shortplot)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".Year", str(year))
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".MPAA", str(officialrating))
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".ItemGUID", seriesId)
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".id", item_id)
            
            WINDOW.setProperty("NextUpEpisodeMB3." + str(item_count) + ".Resume", resume)
            
            WINDOW.setProperty("NextUpEpisodeMB3.Enabled", "true")
            
            item_count = item_count + 1
            
        if(item_count < 10):
            # blank any not available
            for x in range(item_count, 11):           
                WINDOW.setProperty("NextUpEpisodeMB3." + str(x) + ".EpisodeTitle", "")
                WINDOW.setProperty("NextUpEpisodeMB3." + str(x) + ".ShowTitle", "")
                WINDOW.setProperty("NextUpEpisodeMB3." + str(x) + ".EpisodeNo", "")
                WINDOW.setProperty("NextUpEpisodeMB3." + str(x) + ".SeasonNo", "")
                WINDOW.setProperty("NextUpEpisodeMB3." + str(x) + ".Thumb", "")
                WINDOW.setProperty("NextUpEpisodeMB3." + str(x) + ".Path", "")            
                WINDOW.setProperty("NextUpEpisodeMB3." + str(x) + ".Rating", "")
                WINDOW.setProperty("NextUpEpisodeMB3." + str(x) + ".Art(tvshow.fanart)", "")
                WINDOW.setProperty("NextUpEpisodeMB3." + str(x) + ".Art(tvshow.clearlogo)", "")
                WINDOW.setProperty("NextUpEpisodeMB3." + str(x) + ".Art(tvshow.banner)", "")
                WINDOW.setProperty("NextUpEpisodeMB3." + str(x) + ".Art(tvshow.poster)", "")
                WINDOW.setProperty("NextUpEpisodeMB3." + str(x) + ".Plot", "")
                WINDOW.setProperty("NextUpEpisodeMB3." + str(x) + ".Resume", "")        
            
            
            
            
