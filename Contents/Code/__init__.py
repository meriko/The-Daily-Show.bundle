NAME = 'The Daily Show'
TDS_URL = 'http://www.thedailyshow.com'
TDS_FULL_EPISODES = 'http://www.thedailyshow.com/full-episodes'
TDS_CORRESPONDENTS = 'http://www.thedailyshow.com/news-team'
TDS_SEARCH = 'http://www.thedailyshow.com/feeds/search?keywords=&tags=%s&sortOrder=desc&sortBy=date&page=%d'

####################################################################################################
def Start():

	ObjectContainer.title1 = NAME
	HTTP.CacheTime = CACHE_1HOUR
	HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:18.0) Gecko/20100101 Firefox/18.0'

####################################################################################################
@handler('/video/thedailyshow', NAME)
def MainMenu():

	oc = ObjectContainer()

	oc.add(DirectoryObject(key=Callback(FullEpisodes), title=L('fullepisodes')))
	oc.add(DirectoryObject(key=Callback(ParseSearchResults, title2=L('guests'), tags='interviews'), title=L('guests')))
	oc.add(DirectoryObject(key=Callback(CorrespondentBrowser), title=L('correspondents')))
	oc.add(DirectoryObject(key=Callback(ParseSearchResults, title2=L('allvideos')), title=L('allvideos')))
	oc.add(SearchDirectoryObject(identifier='com.plexapp.plugins.thedailyshow', title=L('search'), prompt=L('searchprompt'), term=L('videos')))

	return oc

####################################################################################################
@route('/video/thedailyshow/fullepisodes', allow_sync=True)
def FullEpisodes():

	oc = ObjectContainer(title2=L('fullepisodes'))
	html = HTML.ElementFromURL(TDS_FULL_EPISODES)

	for episode in html.xpath('//ul[@class="more_episode_list"]/li'):
		url = episode.xpath('./a/@href')[0]
		guest = episode.xpath('.//span[@class="guest"]/text()')[0].strip(' -')

		airdate = episode.xpath('.//span[contains(@class, "air_date")]/text()')[0].replace('  ', ' ').strip()
		if airdate.lower() == 'special edition':
			title = 'Special Edition - %s' % guest
		else:
			title = '%s - %s' % (airdate, guest)

		summary = episode.xpath('.//span[@class="details"]/span/text()')[0].strip()
		thumb = '%s?width=640&height=360' % episode.xpath('.//img/@src')[0].split('?')[0]

		try:
			date = url.split('/')[4].split('-')
			date = '%s %s, %s' % (date[1], date[2], date[3])
			originally_available_at = Datetime.ParseDate(date).date()
		except:
			originally_available_at = None

		oc.add(EpisodeObject(
			url = url,
			title = title,
			summary = summary,
			thumb = Resource.ContentsOfURLWithFallback(url=thumb),
			originally_available_at = originally_available_at
		))

	return oc

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
		key = Callback(ParseSearchResults, title2=name, tags=name),
		title = name,
		summary = summary,
		thumb = Resource.ContentsOfURLWithFallback(url=thumb)
	)

####################################################################################################
@route('/video/thedailyshow/search', page=int, allow_sync=True)
def ParseSearchResults(title2, tags=None, page=1):

	oc = ObjectContainer(title2=title2)
	if not tags: tags = ''
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
			thumb = Resource.ContentsOfURLWithFallback(url=thumb),
			originally_available_at = originally_available_at
		))

	if len(html.xpath('//a[@class="search-next"]')) > 0:
		oc.add(NextPageObject(
			key = Callback(ParseSearchResults, title2=title2, tags=tags, page=page+1),
			title = L('more')
		))

	return oc
