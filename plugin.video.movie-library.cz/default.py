# -*- coding: UTF-8 -*-
#/*
# *      Copyright (C) 2011 Libor Zoubek
# *
# *
# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with this program; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *
# */

import re,os,urllib,urllib2
import xbmcaddon,xbmc,xbmcgui,xbmcplugin

__scriptid__   = 'plugin.video.movie-library.cz'
__scriptname__ = 'movie-library.cz'
__addon__      = xbmcaddon.Addon(id=__scriptid__)
__language__   = __addon__.getLocalizedString

sys.path.append( os.path.join ( __addon__.getAddonInfo('path'), 'resources','lib') )

import util,ulozto

ulozto.__addon__ = __addon__
ulozto.__language__ = __language__
ulozto.__scriptid__ = __scriptid__

BASE_URL='http://movie-library.cz/'

def icon(icon):
	icon_file = os.path.join(__addon__.getAddonInfo('path'),'resources','icons',icon)
	if not os.path.isfile(icon_file):
		return 'DefaultFolder.png'
	return icon_file

def search(what):
	if what == '':
		kb = xbmc.Keyboard('',__language__(30003),False)
		kb.doModal()
		if kb.isConfirmed():
			what = kb.getText()
	if not what == '':
		maximum = 20
		try:
			maximum = int(__addon__.getSetting('keep-searches'))
		except:
			util.error('Unable to parse convert addon setting to number')
			pass

		util.add_search(__addon__,'search_history',what,maximum)
		util.reportUsage(__scriptid__,__scriptid__+'/search')
		req = urllib2.Request(BASE_URL+'search.php?q='+what.replace(' ','+'))
		response = urllib2.urlopen(req)
		data = response.read()
		response.close()
		if response.geturl().find('search.php') > -1:
			if data.find('tagy:</h2>') > 0:
				parse_tag_page(data)
			return parse_page(data,response.geturl())
		else:
			#single movie was found
			return parse_item(data)
def furl(url):
	if url.startswith('http'):
		return url
	url = url.lstrip('./')
	return BASE_URL+url

def search_list():
	util.add_dir(__language__(30004),{'search':''},util.icon('search.png'))
	for what in util.get_searches(__addon__,'search_history'):
		util.add_dir(what,{'search':what},menuItems={xbmc.getLocalizedString(117):{'search-remove':what}})
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def search_remove(search):
	util.remove_search(__addon__,'search_history',search)
	xbmc.executebuiltin('Container.Refresh')

def categories():
	util.add_dir(__language__(30003),{'search-list':''},util.icon('search.png'))
	util.add_dir(__language__(30010),{'search-ulozto-list':''},icon('ulozto.png'))
	util.add_local_dir(__language__(30037),__addon__.getSetting('downloads'),util.icon('download.png'))
	data = util.substr(util.request(BASE_URL),'div id=\"menu\"','</td')
	pattern = '<a href=\"(?P<url>[^\"]+)[^>]+>(?P<name>[^<]+)'
	for m in re.finditer(pattern,data,re.IGNORECASE | re.DOTALL ):
		if m.group('url').find('staty') > 0:
			util.add_dir(m.group('name'),{'countries':furl(m.group('url'))})
		else:
			util.add_dir(m.group('name'),{'cat':furl(m.group('url'))})
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def countries(url):
	data = util.substr(util.request(url),'Filmy podle států</h2>','<div id=\"footertext\">')
	pattern = '<a(.+?)href=\"(?P<url>[^\"]+)[^>]+>(?P<name>[^<]+)'
	for m in re.finditer(pattern,data,re.IGNORECASE | re.DOTALL ):
		util.add_dir(m.group('name'),{'cat':furl(m.group('url'))})
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def list_page(url):
	order = orderby()
	if url.find('?') < 0:
		order = '?'+order
	url +=order
	page = util.request(url)
	return parse_page(page,url)

def parse_tag_page(page):
	data = util.substr(page,'<h2>Nalezené tagy:</h2>','</ul>')
	for m in re.finditer('<a href=\"(?P<url>[^\"]+)[^>]+>(?P<name>[^<]+)',data,re.IGNORECASE|re.DOTALL):
		util.add_dir('[tag] '+ m.group('name'),{'cat':furl(m.group('url'))})

def parse_page(page,url):
	lang_filter = __addon__.getSetting('lang-filter').split(',')
	lang_filter_inc  = __addon__.getSetting('lang-filter-include') == 'true'
	# set as empty list when split returns nothing
	if len(lang_filter) == 1 and lang_filter[0] == '':
		lang_filter = []
	data = util.substr(page,'<div class=\"sortlist','<div class=\"pagelist')
	pattern = '<tr><td[^>]+><a href=\"(?P<url>[^\"]+)[^>]+><img src=\"(?P<logo>[^\"]+)(.+?)<a class=\"movietitle\"[^>]+>(?P<name>[^<]+)</a>(?P<data>.+?)/td></tr>'
	for m in re.finditer(pattern, data, re.IGNORECASE | re.DOTALL):
		info = m.group('data')
		year = 0
		plot = ''
		genre = ''
		lang = ''
		rating = 0
		lang_list = []
		for q in re.finditer('<img src=\"(.+?)flags/(?P<lang>[^\.]+)\.png\"',info):
			lang += ' [%s]' % q.group('lang')
			lang_list.append(q.group('lang'))
		if not lang_filter == []:
			filtered = True
			if len(lang_list) > 0:
				for l in lang_list:
					if l in lang_filter:
						filtered = False
			elif lang_filter_inc:
				filtered = False
			if filtered:
				continue

		s  = re.search('<div style=\"color[^<]+</div>(?P<genre>.*?)<br[^>]*>(?P<year>.*?)<',info)
		if s:
			genre = s.group('genre')
			try:
				year = int(re.sub(',.*','',s.group('year')))
			except:
				pass
		r = re.search('<div class=\"ratingval\"(.+?)width:(?P<rating>\d+)px',info)
		if r:
			try:
				rating = float(r.group('rating'))/5
			except:
				pass
		t = re.search('<div style=\"margin-top:5px\">(?P<plot>[^<]+)',info)
		if t:
			plot = t.group('plot')
		util.add_dir(m.group('name')+lang,{'item':furl(m.group('url'))},m.group('logo'),infoLabels={'Plot':plot,'Genre':genre,'Rating':rating,'Year':year})
	data = util.substr(page,'<div class=\"pagelist\"','<div id=\"footertext\">')
	for m in re.finditer('<a style=\"float:(right|left)(.+?)href=\"(.+?)(?P<page>page=\d+)[^>]+>(?P<name>[^<]+)',data,re.IGNORECASE | re.DOTALL):
		logo = 'DefaultFolder.png'
		if m.group('name').find('Další') >= 0:
			logo = util.icon('next.png')
		if m.group('name').find('Předchozí') >= 0:
			logo = util.icon('prev.png')
		util.add_dir(m.group('name'),{'cat':url+'&'+m.group('page')},logo)
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def orderby():
	return '&sort=%s' % __addon__.getSetting('order-by')

def list_item(url):
	return parse_item(util.request(url))

def parse_item(page):
	#search for series items
	data = util.substr(page,'Download:</h3><table>','</table>')
	pattern = '<a href=\"(?P<url>[^\"]+)[^>]+>(?P<name>[^<]+)</a></div></td><td[^>]+>(?P<size>[^<]+)'
	for m in re.finditer(pattern, data, re.IGNORECASE | re.DOTALL):
		iurl = furl(m.group('url'))
		util.add_video('%s (%s)'%(m.group('name'), m.group('size')),
		{'play':iurl},
		menuItems={xbmc.getLocalizedString(33003):{'name':m.group('name'),'download':iurl}}
		)

	# search for movie items
	data = util.substr(page,'Download:</h3>','<div id=\"login-password-box')
	pattern = '<a class=\"under\" href="(?P<url>[^\"]+)[^>]+>(?P<name>[^<]+)</a>(.+?)<abbr[^>]*>(?P<size>[^<]+)'
	for m in re.finditer(pattern, data, re.IGNORECASE | re.DOTALL):
		iurl = furl(m.group('url'))
		util.add_video('%s (%s)'%(m.group('name'), m.group('size')),
		{'play':iurl},
		menuItems={xbmc.getLocalizedString(33003):{'name':m.group('name'),'download':iurl}}
		)
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def play(url):
	stream = resolve(url)
	if stream:
		util.reportUsage(__scriptid__,__scriptid__+'/play')
		print 'Sending %s to player' % stream
		li = xbmcgui.ListItem(path=stream+'&',iconImage='DefaulVideo.png')
		return xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, li)

def resolve(url):
	if ulozto.supports(url):
		uloztourl = url
	else:
		data = util.request(url)
		# find uloz.to url
		m = re.search('window\.location=\'(?P<url>[^\']+)',data,re.IGNORECASE | re.DOTALL)
		if m:
			uloztourl = m.group('url')
		else:
			# daily maximum of requested movies reached (150)
			util.error('daily maximum (150) requests for movie was reached, try it tomorrow')
			return
#		m = re.search('javascript\" src=\"(?P<js>[^\"]+)',data,re.IGNORECASE | re.DOTALL)
#		if m:
#			js = util.request(m.group('js'))
#			challenge = re.search('challenge :[^\']+\'([^\']+)',js,re.IGNORECASE|re.DOTALL).group(1)
#			dialog = xbmcgui.Dialog()
#			dialog.ok(__scriptname__,'ahoj','ahoj')
#			xbmc.executebuiltin('XBMC.Notification(%s,%s,10000,%s)' % (__scriptname__,'','http://www.google.com/recaptcha/api/image?c='+challenge))
#			kb = xbmc.Keyboard('','opis obrazek',False)
#			kb.doModal()
#			if kb.isConfirmed():
#				code = kb.getText()
	stream = ulozto.url(uloztourl)
	if stream == -1:
		xbmcgui.Dialog().ok(__scriptname__,__language__(30002))
		return
	if stream == -2:
		xbmcgui.Dialog().ok(__scriptname__,__language__(30001))
		return
	return stream

def download(url,name):
	downloads = __addon__.getSetting('downloads')
	if '' == downloads:
		xbmcgui.Dialog().ok(__scriptname__,__language__(30031))
		return
	stream = resolve(url)
	if stream:
		util.reportUsage(__scriptid__,__scriptid__+'/download')
		util.download(__addon__,name,stream,os.path.join(downloads,name))

p = util.params()
if p=={}:
	xbmc.executebuiltin('RunPlugin(plugin://script.usage.tracker/?do=reg&cond=31000&id=%s)' % __scriptid__)
	categories()
if 'cat' in p.keys():
	list_page(p['cat'])
if 'countries' in p.keys():
	countries(p['countries'])
if 'item' in p.keys():
	list_item(p['item'])
if 'play' in p.keys():
	play(p['play'])
if 'download' in p.keys():
	download(p['download'],p['name'])
if 'search-list' in p.keys():
	search_list()
if 'search' in p.keys():
	search(p['search'])
if 'search-remove' in p.keys():
	search_remove(p['search-remove'])
if 'search-ulozto-list' in p.keys():
	ulozto.search_list()
if 'search-ulozto' in p.keys():
	ulozto.search(p['search-ulozto'])
if 'list-ulozto' in p.keys():
	ulozto.list_page(p['list-ulozto'])
if 'search-ulozto-remove' in p.keys():
	ulozto.search_remove(p['search-ulozto-remove'])
