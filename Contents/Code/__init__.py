NAME = 'The Daily Show'
TDS_URL = 'http://thedailyshow.cc.com'

EPISODES_URL = 'http://thedailyshow.cc.com/full-episodes'
EPISODES_FEED = '%s/feeds/f1010/1.0/a77b2fb1-bb8e-498d-bca1-6fca29d44e62/2796e828-ecfd-11e0-aca6-0026b9414f30/%%s' % TDS_URL
#                                   ^^^ section/videotype id(?)          ^^^ show id                          ^^^ most recent episode id

NEWSTEAM_MEMBERS = '%s/feeds/f1060/1.0/93a0d300-98ac-4a75-9d4f-09577c87cfc4' % TDS_URL
NEWSTEAM_MEMBER_CLIPS = '%s/feeds/f1054/1.0/e33d9f3c-aa11-43cb-8186-93ff42490331/%%s/%%d' % TDS_URL

TDS_SEARCH = '%s/feeds/f1030/1.0?keywords=&tags=%%s&sortBy=date&startingIndex=%%d' % TDS_URL

####################################################################################################
def Start():

	ObjectContainer.title1 = NAME
	HTTP.CacheTime = CACHE_1HOUR
	HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.152 Safari/537.36'

####################################################################################################
@handler('/video/thedailyshow', NAME)
def MainMenu():

	oc = ObjectContainer()

	if Client.Platform and Client.Platform not in ('Android'):
		oc.add(DirectoryObject(key=Callback(FullEpisodes), title=L('fullepisodes')))

	oc.add(DirectoryObject(key=Callback(ParseSearchResults, title2=L('guests'), tags='interviews'), title=L('guests')))
	oc.add(DirectoryObject(key=Callback(NewsTeam), title=L('correspondents')))
	oc.add(DirectoryObject(key=Callback(ParseSearchResults, title2=L('allvideos')), title=L('allvideos')))
	oc.add(SearchDirectoryObject(identifier='com.plexapp.plugins.thedailyshow', title=L('search'), prompt=L('searchprompt'), term=L('videos')))

	return oc

####################################################################################################
@route('/video/thedailyshow/fullepisodes', allow_sync=True)
def FullEpisodes():

	oc = ObjectContainer(title2=L('fullepisodes'))

	html = HTML.ElementFromURL(EPISODES_URL)
	episode_id = html.xpath('//div[@id="video_player"]/@data-mgid')[0].split(':')[-1]

	json_obj = JSON.ObjectFromURL(EPISODES_FEED % episode_id)

	for result in json_obj['result']['episodes']:

		if result['type'] != 'episode':
			continue

		oc.add(EpisodeObject(
			url = result['canonicalURL'].replace('/episodes/', '/full-episodes/'),
			title = result['title'],
			summary = result['description'] if result['description'] != '' else result['shortDescription'],
			duration = int(float(result['duration']))*1000,
			thumb = Resource.ContentsOfURLWithFallback(url=result['images'][0]['url'] if len(result['images']) > 0 else ''),
			originally_available_at = Datetime.FromTimestamp(int(result['publishDate']))
		))

	return oc

####################################################################################################
@route('/video/thedailyshow/newsteam')
def NewsTeam():

	oc = ObjectContainer(title2=L('correspondents'))

	json_obj = JSON.ObjectFromURL(NEWSTEAM_MEMBERS)

	for member in json_obj['result']['promo']['relatedItems']:

		name = member['promotedItem']['name']
		member_id = member['promotedItem']['id']
		thumb = member['promotedItem']['images'][0]['url']

		oc.add(DirectoryObject(
			key = Callback(NewsTeamMember, name=name, member_id=member_id),
			title = name,
			thumb = Resource.ContentsOfURLWithFallback(url=thumb)
		))

	return oc

####################################################################################################
@route('/video/thedailyshow/newsteam/{member_id}/{page}', page=int, allow_sync=True)
def NewsTeamMember(name, member_id, page=1):

	oc = ObjectContainer(title2=name)

	json_obj = JSON.ObjectFromURL(NEWSTEAM_MEMBER_CLIPS % (member_id, page))

	for result in json_obj['result']['videos']:

		if result['type'] != 'video':
			continue

		oc.add(VideoClipObject(
			url = result['canonicalURL'],
			title = result['title'],
			summary = result['description'] if result['description'] != '' else result['shortDescription'],
			duration = int(float(result['duration']))*1000,
			thumb = Resource.ContentsOfURLWithFallback(url=result['images'][0]['url'] if len(result['images']) > 0 else ''),
			originally_available_at = Datetime.FromTimestamp(int(result['publishDate']))
		))

	if 'nextPageURL' in json_obj['result'] and json_obj['result']['nextPageURL'] != '':
		oc.add(NextPageObject(
			key = Callback(NewsTeamMember, name=name, member_id=member_id, page=page+1),
			title = L('more')
		))

	return oc

####################################################################################################
@route('/video/thedailyshow/search', page=int, allow_sync=True)
def ParseSearchResults(title2, tags='', page=0):

	oc = ObjectContainer(title2=title2)
	url = TDS_SEARCH % (String.Quote(tags), page*25)

	json_obj = JSON.ObjectFromURL(url, cacheTime=CACHE_1HOUR)

	for result in json_obj['result']['results']:

		if result['type'] != 'video':
			continue

		oc.add(VideoClipObject(
			url = result['canonicalURL'],
			title = result['title'],
			summary = result['description'],
			duration = int(float(result['duration']))*1000,
			thumb = Resource.ContentsOfURLWithFallback(url=result['images'][0]['url']),
			originally_available_at = Datetime.FromTimestamp(int(result['publishDate']))
		))

	if 'nextPageURL' in json_obj['result'] and json_obj['result']['nextPageURL'] != '':
		oc.add(NextPageObject(
			key = Callback(ParseSearchResults, title2=title2, tags=tags, page=page+1),
			title = L('more')
		))

	return oc
