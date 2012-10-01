ParseSearchResults = SharedCodeService.ParseSearchResults.ParseSearchResults

RE_BIOGRAPHY = Regex(r'Biography:\n*(.*)', Regex.DOTALL)
RE_TIDY_STRING = Regex(r'^\s*(\S.*?\S?)\s*$')

TDS_URL = 'http://www.thedailyshow.com'
TDS_FULL_EPISODES = 'http://www.thedailyshow.com/full-episodes/'
TDS_CORRESPONDENTS = 'http://www.thedailyshow.com/news-team'

ICON = 'icon-default.jpg'
ART = 'art-default.jpg'

DEBUG_XML_RESPONSE = False
CACHE_INTERVAL = 1800 # Since we are not pre-fetching content this cache time seems reasonable
CACHE_CORRESPONDENT_LIST_INTERVAL = 604800 # 1 Week
CACHE_CORRESPONDENT_BIO_INTERVAL = 7776000 # 3 Months, these pages change very rarely

####################################################################################################
def Start():

  ObjectContainer.art = R(ART)
  ObjectContainer.title1 = L('tds')
  DirectoryObject.thumb = R(ICON)

  HTTP.CacheTime = CACHE_INTERVAL

####################################################################################################
def UpdateCache():

  # The only sections that a slow to load as the Correspondent and Alumni sections
  # So pre cache these, with a long cache time for the pages...
  CorrespondentBrowser(cacheUpdate=True)

####################################################################################################
@handler('/video/thedailyshow', L('tds'), art=ART, thumb=ICON)
def MainMenu():

  oc = ObjectContainer()

  oc.add(DirectoryObject(key=Callback(FullEpisodes), title=L('fullepisodes')))
  oc.add(DirectoryObject(key=Callback(GuestBrowser), title=L('guests')))
  oc.add(DirectoryObject(key=Callback(CorrespondentBrowser), title=L('correspondents')))
  oc.add(DirectoryObject(key=Callback(AllVideosBrowser), title=L('allvideos')))

  if DEBUG_XML_RESPONSE:
    Log(oc.Content())

  return oc

####################################################################################################
def FullEpisodes():

  oc = ObjectContainer(title2=L('fullepisodes'))

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
      date = Datetime.ParseDate(aired.replace('Aired: ','').strip())
      episodeMap[date] = episode

  sortedEpisodes = episodeMap.keys()[:]
  sortedEpisodes.sort()
  sortedEpisodes.reverse()

  for episodeKey in sortedEpisodes:
    #Log("Key:"+str(episodeKey))
    episode = episodeMap[episodeKey]
    title = episode.xpath(".//div[@class='moreEpisodesTitle']/span/a")[0].text
    description = episode.xpath(".//div[@class='moreEpisodesDescription']/span")[0].text
    url = episode.xpath(".//div[@class='moreEpisodesImage']/a")[0].get("href")
    thumb = episode.xpath(".//div[@class='moreEpisodesImage']/a/img")[0].get("src")
    # Load larger images
    thumb = thumb.replace("&width=165","&width=495")

    oc.add(EpisodeObject(url=url, title=title, summary=description, thumb=Resource.ContentsOfURLWithFallback(url=thumb, fallback=ICON)))

  return oc

####################################################################################################
def GuestBrowser():
  return ParseSearchResults(L('tds'), L('guests'), tags='interviews')

####################################################################################################
def CorrespondentBrowser(cacheUpdate=False):

  oc = ObjectContainer(title2=L('correspondents'))

  correspondentsPage = HTML.ElementFromURL(TDS_CORRESPONDENTS, cacheTime=CACHE_CORRESPONDENT_LIST_INTERVAL)
  correspondents = correspondentsPage.xpath("//div[@class='team-details']/a")

  for correspondent in correspondents:
    item = GetCorrespondentBio(correspondent, section=L('correspondents'))
    oc.add(item)
    #oc.add(DirectoryObject(key=Callback(GetCorrespondentBio, correspondent, section=L('correspondents'))))

  if DEBUG_XML_RESPONSE and not cacheUpdate:
    Log(oc.Content())

  return oc

####################################################################################################
def GetCorrespondentBio(correspondent, section):

  if len ( correspondent.xpath(".//span") ) > 0:
    name = correspondent.xpath(".//span")[0].text
  else:
    name = TidyString(correspondent.text)

  url = correspondent.get("href")
  if 'http://' in url:
    pass
  else:
    url = TDS_URL + url

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
	  description = RE_BIOGRAPHY.search(description).group(1)
          #description = re.search (r'Biography:\n*(.*)', description, re.DOTALL).group(1)
        except:
          description = ''

    except:  # Some don't have bios...
      description = ''
    thumb = info.xpath('.//div[@class="middle"]/div[@class="imageHolder"]/img')[0].get("src")
  except:
    description = ''
    thumb = ''

  item = DirectoryObject(key=Callback(CorrespondentSearch, section=section, name=name),
         title=name, summary=description, thumb=Resource.ContentsOfURLWithFallback(url=thumb, fallback=ICON))

  return item

####################################################################################################
def CorrespondentSearch(section, name):
  return ParseSearchResults(section, name, tags=name, page=1)

####################################################################################################
def AllVideosBrowser():
  return ParseSearchResults(L('tds'), L('allvideos'), page=1)

####################################################################################################
def TidyString(stringToTidy):

  # Function to tidy up strings works ok with unicode, 'strip' seems to have issues in some cases so we use a regex
  if stringToTidy:
    # Remove new lines
    stringToTidy.replace('\n', ' ')

    # Strip leading / trailing spaces
    stringSearch = RE_STRING_TIDY.search(stringToTidy)

    if stringSearch == None:
      return ''
    else:
      return stringSearch.group(1)
  else:
    return ''
