import re
 
####################################################################################################
 
TDS_PREFIX                  = '/video/thedailyshow'
 
TDS_URL                     = 'http://www.thedailyshow.com'
TDS_FULL_EPISODES           = 'http://www.thedailyshow.com/full-episodes/'
TDS_CORRESPONDENTS          = 'http://www.thedailyshow.com/news-team'

# All videos
# http://www.thedailyshow.com/feeds/search?keywords=&tags=&sortOrder=desc&sortBy=views&page=1

# Search guests: sortBy=views = most viewed also sortBy=original_air_date_d
# http://www.thedailyshow.com/feeds/search?keywords=&tags=interviews&sortOrder=desc&sortBy=views&page=1

# For a correspondent
#http://www.thedailyshow.com/feeds/search?keywords=&tags=Samantha%20Bee&sortOrder=desc&sortBy=views&page=1

TDS_SEARCH = "http://www.thedailyshow.com/feeds/search?keywords=%s&tags=%s&sortOrder=desc&sortBy=%s&page=%d"
SORT_AIRED = "original_air_date_d"
SORT_VIEWED = "views"
SORT_ORDER_KEY = "sort_order"

 
DEBUG_XML_RESPONSE             = False
CACHE_INTERVAL                       = 1800 # Since we are not pre-fetching content this cache time seems reasonable 
CACHE_SEARCH_INTERVAL             = 600
CACHE_CORRESPONDENT_LIST_INTERVAL    = 604800 # 1 Week
CACHE_CORRESPONDENT_BIO_INTERVAL     = 7776000 # 3 Months, these pages change very rarely
 
 
###################################################################################################
 
def Start():
  Plugin.AddPrefixHandler(TDS_PREFIX, MainMenu, L('tds'), 'icon-default.jpg', 'art-default.jpg')
  Plugin.AddViewGroup('List', viewMode='List', mediaType='items')
  Plugin.AddViewGroup('Details', viewMode='InfoList', mediaType='items')
  MediaContainer.content = 'Items'
  MediaContainer.art = R('art-default.jpg')
  MediaContainer.viewGroup = 'Details'
  Dict[SORT_ORDER_KEY] = SORT_AIRED
  HTTP.CacheTime = CACHE_INTERVAL
 
def UpdateCache():
  # The only sections that a slow to load as the Correspondent and Alumni sections
  # So pre cache these, with a long cache time for the pages...
  CorrespondentBrowser(None, cacheUpdate=True)
  AlumniBrowser(None, cacheUpdate=True)
 
 
def MainMenu():
 
  dir = MediaContainer()
  dir.title1 = L('tds')
  dir.viewGroup = 'List'
 
  dir.Append(Function(DirectoryItem(FullEpisodes, title=L('fullepisodes'), thumb=R('icon-default.jpg'))))
  dir.Append(Function(DirectoryItem(GuestBrowser, title=L('guests'), thumb=R('icon-default.jpg'))))
  dir.Append(Function(DirectoryItem(CorrespondentBrowser, title=L('correspondents'), thumb=R('icon-default.jpg'))))
  #dir.Append(Function(DirectoryItem(AlumniBrowser, title=L('alumni'), thumb=R('icon-default.jpg'))))
  dir.Append(Function(DirectoryItem(AllVideosBrowser, title=L('allvideos'), thumb=R('icon-default.jpg'))))
  dir.Append(Function(SearchDirectoryItem(Search, title=L('search'), prompt=L('searchprompt'), thumb=R('search.png'))))
 
  if DEBUG_XML_RESPONSE:
    Log(dir.Content())
  return dir
 
def FullEpisodes(sender):
  dir = MediaContainer()
  dir.title1 = L('tds')
  dir.title2 = L('fullepisodes')
 
  seasons = []
  allSeasons = HTML.ElementFromURL(TDS_FULL_EPISODES)
  for season in allSeasons.xpath('//div[@class="seasons"]//a'):
      url = season.get('id')
      seasons.append(url.replace(' ','%20'))
  
  episodeMap = dict()
  for season in seasons:
     
      episodes = HTML.ElementFromURL(season).xpath('.//div[@class="moreEpisodesContainer"]')
      episodes.extend(HTML.ElementFromURL(season).xpath('.//div[@class="moreEpisodesContainer-selected"]'))

      for episode in episodes:
          title = episode.xpath(".//div[@class='moreEpisodesTitle']/span/a")[0].text
          aired = episode.xpath(".//div[@class='moreEpisodesAirDate']/span")[0].text
          Log(title+":"+aired)
          date = Datetime.ParseDate(aired.replace('Aired: ','').strip())
          episodeMap[date] = episode
  
  sortedEpisodes = episodeMap.keys()[:]
  sortedEpisodes.sort()
  sortedEpisodes.reverse()
  for episodeKey in sortedEpisodes:
          Log("Key:"+str(episodeKey))
          episode = episodeMap[episodeKey]
          title = episode.xpath(".//div[@class='moreEpisodesTitle']/span/a")[0].text
          description = episode.xpath(".//div[@class='moreEpisodesDescription']/span")[0].text
          url = episode.xpath(".//div[@class='moreEpisodesImage']/a")[0].get("href")
          thumb = episode.xpath(".//div[@class='moreEpisodesImage']/a/img")[0].get("src")
          # Load larger images
          thumb = thumb.replace("&width=165","&width=495")
 
          dir.Append(WebVideoItem(url, title=title, summary=description, duration='', thumb=thumb))
  return dir
 
def GuestBrowser(sender):
  return ParseSearchResults(None, L('tds'), L('guests'), tags='interviews')
 
def CorrespondentBrowser(sender, cacheUpdate=False):
 
  dir = MediaContainer()
  dir.title1 = L('tds')
  dir.title2 = L('correspondents')
 
  correspondentsPage = HTML.ElementFromURL(TDS_CORRESPONDENTS, cacheTime=CACHE_CORRESPONDENT_LIST_INTERVAL)
  correspondents = correspondentsPage.xpath("//div[@class='team-details']/a")
 
  for correspondent in correspondents:
    dir.Append ( GetCorrespondentBio(correspondent, section=L('correspondents')) )
 
  if DEBUG_XML_RESPONSE and not cacheUpdate:
    Log(dir.Content())
  return dir
 
def AlumniBrowser(sender, cacheUpdate=False):
 
  dir = MediaContainer()
  dir.title1 = L('tds')
  dir.title2 = L('alumni')
 
  correspondentsPage = HTML.ElementFromURL(TDS_CORRESPONDENTS, cacheTime=CACHE_CORRESPONDENT_LIST_INTERVAL)
  correspondents = correspondentsPage.xpath("//div[@class='right']/ul/li/a")
  
  for correspondent in correspondents:
    dir.Append ( GetCorrespondentBio(correspondent, section=L('alumni')) )
 
  if DEBUG_XML_RESPONSE and not cacheUpdate:
    Log(dir.Content())
  return dir
 
def GetCorrespondentBio (correspondent, section):
 
  if len ( correspondent.xpath(".//span") ) > 0:
    name = correspondent.xpath(".//span")[0].text
  else:
    name = TidyString(correspondent.text)
 
  url = TDS_URL + correspondent.get("href")
 
  description = ''
  thumb = ''
  # Try to fetch their details, gives 404 for some correspondents at the time of writing
  try:
    info = HTML.ElementFromURL(url, cacheTime=CACHE_CORRESPONDENT_BIO_INTERVAL)
    try:
      for part in info.xpath(".//div[@class='middle']/div[@class='textHolder']/p"):
        description += part.text_content() + '\n\n'
      # If we didn't find the bio (Samantha Bee I'm looking at you) try a different path
      if description == '':
        description = info.xpath(".//div[@class='middle']/div[@class='textHolder']")[0].text_content()
        # See if the text contains a bio
        try:
          description = re.search (r'Biography:\n*(.*)', description, re.DOTALL).group(1)
        except:
          description = ''
        
    except:  # Some don't have bios...
      description = ''
    thumb = info.xpath('.//div[@class="middle"]/div[@class="imageHolder"]/img')[0].get("src")
  except:
    description = ''
    thumb = ''
 
  item = Function(DirectoryItem(CorrespondentSearch, title=name, summary=description, thumb=thumb), section=section, name=name)
  return item
 
def CorrespondentSearch(sender, section, name):
  return ParseSearchResults(None, section, name, tags=name)
 
def AllVideosBrowser(sender):
  return ParseSearchResults(None, L('tds'), L('allvideos'))
 
def Search(sender, query):
  return ParseSearchResults(None, L('tds'), L('search'), keywords=query)
 
def OrderByDate(sender, key, **kwargs):
    Dict[SORT_ORDER_KEY] = SORT_AIRED
     
def OrderByViews(sender, key, **kwargs):
    Dict[SORT_ORDER_KEY] = SORT_VIEWED
 
def ParseSearchResults(sender, title1, title2, keywords='', tags='', page=1):
  menu = ContextMenu(includeStandardItems=False)
  if Dict[SORT_ORDER_KEY] == SORT_AIRED:
        menu.Append(Function(DirectoryItem(OrderByViews, title='Order by Most Viewed')))
  elif Dict[SORT_ORDER_KEY] == SORT_VIEWED:
        menu.Append(Function(DirectoryItem(OrderByDate, title='Order by Aired Date')))
  dir = MediaContainer(noCache=True, contextMenu=menu)
  if page > 1:
    dir.title1 = title2
    dir.title2 = L('page') + ' ' + str(page)
  else:
    dir.title1 = title1
    dir.title2 = title2
 
    # Sort order selected, run the query
 
  pageQueryUrl = TDS_SEARCH % (String.Quote(keywords), String.Quote(tags), Dict[SORT_ORDER_KEY], page)
  Log("Query URL:"+pageQueryUrl)
  results = HTML.ElementFromURL(pageQueryUrl, cacheTime=CACHE_SEARCH_INTERVAL)
  for result in results.xpath('//div[@class="search-results"]/div[@class="entry"]'):
      
      clipUrl = result.xpath(".//span[@class='title']/a")[0].get("href")
      subtitle = result.xpath('.//div[@class="info_holder"]/div[@class="section"]')[0].text
      title = result.xpath('.//span[@class="title"]/a')[0].text
  # Some results are missing images
      try:
	    thumb = result.xpath(".//img")[0].get("src")
	# Scale up the image a bit
	    thumb = re.sub ( r'width=100', r'width=300', thumb)
      except:
	    thumb = ''
      description = result.xpath('.//span[@class="description"]')[0].text
      dir.Append(WebVideoItem(clipUrl, title=title, subtitle=subtitle, summary=description, duration='', thumb=thumb, contextKey=title, contextArgs={}))


# See if we have a next page link
# The last but one page of search results does not have a 'next' button so instead we look for a following numbered page
  if len (results.xpath("//a[@class='search-page search-page-current']/following-sibling::a[@class='search-page']") ) > 0:
      dir.Append(Function(DirectoryItem(ParseSearchResults, title=L('more'), summary='', thumb=R('more.png')), title1=title1, title2=title2, keywords=keywords, tags=tags, page=page+1))

 
  if DEBUG_XML_RESPONSE:
    Log(dir.Content())
  return dir
 
 
def TidyString(stringToTidy):
  # Function to tidy up strings works ok with unicode, 'strip' seems to have issues in some cases so we use a regex
  if stringToTidy:
    # Strip new lines
    stringToTidy = re.sub(r'\n', r' ', stringToTidy)
    # Strip leading / trailing spaces
    stringSearch = re.search(r'^\s*(\S.*?\S?)\s*$', stringToTidy)
    if stringSearch == None:
      return ''
    else:
      return stringSearch.group(1)
  else:
    return ''
 
 