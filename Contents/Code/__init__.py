NAME = 'The Daily Show'
ICON = 'icon-default.png'
ART = 'art-default.jpg'

TDS_URL = 'http://www.thedailyshow.com'
TDS_FULL_EPISODES = 'http://www.thedailyshow.com/full-episodes'
TDS_CORRESPONDENTS = 'http://www.thedailyshow.com/news-team'
TDS_SEARCH = 'http://www.thedailyshow.com/feeds/search?keywords=&tags=%s&sortOrder=desc&sortBy=date&page=%d'

####################################################################################################
def Start():

	ObjectContainer.art = R(ART)
	ObjectContainer.title1 = NAME
	DirectoryObject.thumb = R(ICON)
	NextPageObject.thumb = R(ICON)
	EpisodeObject.thumb = R(ICON)
	VideoClipObject.thumb = R(ICON)

	HTTP.CacheTime = CACHE_1HOUR
	HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:18.0) Gecko/20100101 Firefox/18.0'

####################################################################################################
@handler('/video/thedailyshow', NAME, art=ART, thumb=ICON)
def MainMenu():

	oc = ObjectContainer()

	oc.add(DirectoryObject(key=Callback(FullEpisodes), title=L('fullepisodes')))
	oc.add(DirectoryObject(key=Callback(GuestBrowser), title=L('guests')))
	oc.add(DirectoryObject(key=Callback(CorrespondentBrowser), title=L('correspondents')))
	oc.add(DirectoryObject(key=Callback(AllVideosBrowser), title=L('allvideos')))
	oc.add(SearchDirectoryObject(identifier='com.plexapp.plugins.thedailyshow', title=L('search'), prompt=L('searchprompt'), thumb=R('search.png')))

	return oc

####################################################################################################
@route('/video/thedailyshow/fullepisodes')
def FullEpisodes():

	oc = ObjectContainer(title2=L('fullepisodes'))
	html = HTML.ElementFromURL(TDS_FULL_EPISODES)
	video = []

	for url in html.xpath('//div[@class="seasons"]/a/@id'):
		for episode in HTML.ElementFromURL(url).xpath('//div[starts-with(@class, "moreEpisodesContainer")]', sleep=0.5):

			if episode.get('id') in video: continue
			video.append(episode.get('id')) # Prevent duplicates

			url = episode.xpath('.//div[@class="moreEpisodesTitle"]/span/a/@href')[0]
			title = episode.xpath('.//div[@class="moreEpisodesTitle"]/span/a/text()')[0]
			summary = episode.xpath('.//div[@class="moreEpisodesDescription"]/span/text()')[0]
			thumb = episode.xpath('.//div[@class="moreEpisodesImage"]/a/img/@src')[0].split('?')[0]

			air_date = episode.xpath('.//div[@class="moreEpisodesAirDate"]/span/text()')[0].replace('Aired: ', '')
			originally_available_at = Datetime.ParseDate(air_date).date()

			oc.add(EpisodeObject(
				url = url,
				title = title,
				summary = summary,
				thumb = Resource.ContentsOfURLWithFallback(url=thumb, fallback=ICON),
				originally_available_at = originally_available_at
			))

	oc.objects.sort(key=lambda obj: obj.originally_available_at, reverse=True)
	return oc

####################################################################################################
@route('/video/thedailyshow/guests')
def GuestBrowser():

	return ParseSearchResults(title2=L('guests'), tags='interviews')

####################################################################################################
@route('/video/thedailyshow/correspondents')
def CorrespondentBrowser():

	oc = ObjectContainer(title2=L('correspondents'))

	for correspondent in HTML.ElementFromURL(TDS_CORRESPONDENTS).xpath('//div[@class="team-details"]/a'):
		item = GetCorrespondentBio(correspondent)
		oc.add(item)

	return oc

####################################################################################################
def GetCorrespondentBio(correspondent):

	name = correspondent.xpath('./span/text()')[0].replace('_', ' ')
	url = correspondent.get('href')

	if not url.startswith('http://'):
		url = TDS_URL + url

	summary = ''
	thumb = ''

	# Try to fetch their details
	try:
		info = HTML.ElementFromURL(url, cacheTime=CACHE_1MONTH)
		biography = info.xpath('//div[@class="textHolder"]')[0].text_content()
		summary = biography.split('Biography:',1)[1].strip()

		thumb = info.xpath('//div[@class="middle"]/div[@class="imageHolder"]/img/@src')[0].split('?')[0]
	except:
		pass

	return DirectoryObject(
		key = Callback(CorrespondentSearch, name=name),
		title = name,
		summary = summary,
		thumb = Resource.ContentsOfURLWithFallback(url=thumb, fallback=ICON)
	)

####################################################################################################
@route('/video/thedailyshow/video/correspondents')
def CorrespondentSearch(name):

	return ParseSearchResults(title2=name, tags=name)

####################################################################################################
@route('/video/thedailyshow/video/all')
def AllVideosBrowser():

	return ParseSearchResults(title2=L('allvideos'))

####################################################################################################
@route('/video/thedailyshow/search', page=int)
def ParseSearchResults(title2='', tags='', page=1):

	oc = ObjectContainer(title2=title2)
	url = TDS_SEARCH % (String.Quote(tags), page)
	html = HTML.ElementFromURL(url, cacheTime=CACHE_1HOUR)

	for result in html.xpath('//div[@class="search-results"]/div[@class="entry"]'):
		url = result.xpath('.//span[@class="title"]/a/@href')[0]
		title = result.xpath('.//span[@class="title"]/a/text()')[0]
		summary = result.xpath('.//span[@class="description"]/text()')[0]

		try:
			thumb = result.xpath('.//img/@src')[0].split('?')[0]
			thumb = '%s?width=640' % thumb
		except:
			thumb = ''

		air_date = result.xpath('.//div[@class="info_holder"]//span[contains(., "Aired:")]/following-sibling::text()')[0]
		originally_available_at = Datetime.ParseDate(air_date).date()

		if summary[-7:-6] == '(':
			(summary, duration) = summary.rsplit(' (', 1)
			duration = Datetime.MillisecondsFromString(duration.strip(')'))

		oc.add(VideoClipObject(
			url = url,
			title = title,
			summary = summary,
			duration = duration,
			thumb = Resource.ContentsOfURLWithFallback(url=thumb, fallback=ICON),
			originally_available_at = originally_available_at
		))

	if len(html.xpath('//a[@class="search-next"]')) > 0:
		oc.add(NextPageObject(
			key = Callback(ParseSearchResults, title2=title2, tags=tags, page=page+1),
			title = L('more')
		))

	return oc
