#!/usr/bin/env python

# -*- coding: UTF8 -*-

#***************************************************************************
#*                                                                         *
#*   This program is free software; you can redistribute it and/or modify  *
#*   it under the terms of the GNU General Public License (GPL)            *
#*   as published by the Free Software Foundation; either version 2 of     *
#*   the License, or (at your option) any later version.                   *
#*   for detail see the LICENCE text file.                                 *
#*                                                                         *
#*   This program is distributed in the hope that it will be useful,       *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#*   GNU Library General Public License for more details.                  *
#*                                                                         *
#*   You should have received a copy of the GNU Library General Public     *
#*   License along with this program; if not, write to the Free Software   *
#*   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
#*   USA                                                                   *
#*                                                                         *
#***************************************************************************

'''
Fluxtwitter 0.6 - 19.08.2011

author: Yorik van Have
url: http://yorik.uncreated.net

A very simple app to connect to your twitter account, fetch your friends
timeline and display it in a pidgin-like window. Supports fluxbox
pseudo-transparency.

History:

0.1 - 12.08.2009 - First version
0.2 - 19.11.2009 - Added fluxbox pseudo-transparency support
0.3 - 10.04.2010 - Tweets now accumulate until you open the window
0.4 - 24.04.2010 - Using monsterID in case twitter avatar doesn't work
0.5 - 03.10.2010 - Implemented OAuth authentication
0.6 - 19.08.2011 - Bugfixes and added text output option

Usage:

fluxtwitter can be invoked with no arguments, in which case it will run in
normal GUI mode. If it is the first time you use it, you'll be asked to
connect it to your account on the twitter website. After that, your settings
will be stored for next times. The application then connects to your twitter
account and retrieves your timeline.

By default tweets will stack until you read them. The trat icon changes to
green to tell you there are new tweets to be read. You can enable fluxbox
pseudo-transparency in the options, but it will work well only if your
background image is exactly the pixel size of your screen.

Fluxtwitter can also be run in text mode, in which case it will simply
display the last tweets on the standard output. Use this for example
to add tweets in a conky setup, with a line like:
${execi 120 fluxtwitter.py -t}

Options:

-t or --text: displays a list of tweets without opening the GUI,
-h or --help: displays this help text
'''

import sys, os, gtk, gobject, urllib, re, subprocess, time, string, hashlib, simplejson, getopt
from twitter import Api, User
try:
    import oauth.oauth as oauth
except ImportError:
    import oauth

# defaults

CONSUMERKEY = "G2EgGMNLFAJxvebsuv9D8A"
CONSUMERSECRET = "zstJsJxBAaND3ria36Mo6khdgyBEgc9gyz9tDdgg"
ACCESSTOKEN = None
DISPLAYTWEETS = 8 # minimum number of tweets displayed
INTERVAL = 120 # update interval in seconds
BROWSER = "x-www-browser" # default browser
TOOLBARHEIGHT = 19 # height of your dektop toolbar, for calculating bg offset
TRANSPARENCY = 50 # transparency level
COMPOSITE = True # if we apply pseudo-transparency or not
COMPOSITECOLOR = 0xffffff00 # color to composite the bg image to
STACKMODE = True # if true, tweets will stack up until you read them
LOGGING = False # if true, a logfile will be created
REQUEST_TOKEN_URL = 'https://twitter.com/oauth/request_token'
ACCESS_TOKEN_URL = 'https://twitter.com/oauth/access_token'
AUTHORIZATION_URL = 'http://twitter.com/oauth/authorize'
SIGNIN_URL = 'http://twitter.com/oauth/authenticate'

fluxicon=[
"16 16 17 1",
" 	c None",
".	c #060911",
"+	c #011136",
"@	c #022274",
"#	c #002CA7",
"$	c #1E2F58",
"%	c #313434",
"&	c #3D360B",
"*	c #0045DE",
"=	c #505461",
"-	c #7A6700",
";	c #8B8B8B",
">	c #B89F00",
",	c #B6B8B5",
"'	c #F9D900",
")	c #DCDCD7",
"!	c #FBFDFA",
"..++++..        ",
" @#######@+     ",
" @#@$$$@##@$.   ",
" @@=)!);@=));.  ",
" @=!!!!!,;)!!=. ",
" @,!!!!%%%%!!;+ ",
" @,!!!)....,!;@ ",
"+#;!!!!....)!$#+",
"+#$!!!!;.+$;%@@.",
" ##=)!!!=$&->>>&",
" @*#$;;&>''''''&",
" +**#.-''''''''&",
"  @**#=->''''''&",
"   @*#@#@&>'''> ",
"    .@#***$-'>& ",
"       +++  &&  "
]

fluxiconalt=[
"16 16 17 1",
" 	c None",
".	c #753F00",
"+	c #804300",
"@	c #884900",
"#	c #914B00",
"$	c #9D5300",
"%	c #AC5C01",
"&	c #B15F00",
"*	c #BB6201",
"=	c #C06500",
"-	c #D17000",
";	c #DA7500",
">	c #DE7800",
",	c #E67903",
"'	c #EE7E00",
")	c #F68500",
"!	c #FE8600",
" %>,,,>=@       ",
" !     +*'>     ",
" &@ .-%   %!@   ",
" > >- #'.)$&!@  ",
" '#&    !   @!  ",
" ,,    ,-!>  '; ",
" >,    !)')  ,, ",
" ,'    !=!) .-, ",
" ,%%   *!)'>!>! ",
" ' '    ')'-$.*#",
" '  >>,)*     +=",
" #=  !%       $%",
"  '   ,)#     ; ",
"   '+>'$-)@   ' ",
"    >'+   !' '  ",
"      =,,>+ )@  "
]

iconnew = [
"16 16 17 1",
" 	c None",
".	c #080A02",
"+	c #102E06",
"@	c #174A00",
"#	c #444A3A",
"$	c #545200",
"%	c #2C7200",
"&	c #72756B",
"*	c #7C7B7D",
"=	c #62A200",
"-	c #8A8C89",
";	c #B69B00",
">	c #AFAFB0",
",	c #93E100",
"'	c #C4C3C5",
")	c #FCDB00",
"!	c #F7F9F6",
" .++++++.       ",
"  @%%%%%%%@.    ",
"  +%@++@%%@+.   ",
"  @@>!!!#@'!'.  ",
"  %*!!!!!*!!!*. ",
" .@'!!!'.*.!!'+ ",
" .@!!!!-...-!'% ",
" .%>!!!>...>!#,.",
" .=#!!!!#.%&#@@.",
" .==*!!!'+$$;))$",
"  ===+&#$))))))$",
"  +,,%$))))))))$",
"   =,,%$;)))))).",
"    =,%$=$;))); ",
"     .=,,,=$)). ",
"       .$+  .+  "
]

iconnewalt = [
"16 16 17 1",
" 	c None",
".	c #130D07",
"+	c #251300",
"@	c #412500",
"#	c #6F4203",
"$	c #946405",
"%	c #8C6B41",
"&	c #BE7400",
"*	c #A17F48",
"=	c #B78A00",
"-	c #9D9489",
";	c #F89400",
">	c #E7BF00",
",	c #FDBF00",
"'	c #D8CFC7",
")	c #FEDC00",
"!	c #FCFEFA",
" +++@++.        ",
" @;;;;;;&$+     ",
" .;;;&&;;;&#    ",
" +;&-!'%;$''#   ",
" @;'!!!!%!!!'@  ",
" #$!!!!--.-!!$+ ",
" $*!!!!....!!$# ",
" &$!!!!....!!=$ ",
" &&'!!!-.$*-#=$ ",
" $,$!!!!-$==>)= ",
" @,,&*-$>)))))>.",
"  =,,$>)))))))>.",
"  @,,,=$>)))))= ",
"   @>=$==$>)))@ ",
"    +$>)))$=)$  ",
"      .+@+  @   "
]

# debug logging
if LOGGING:
        fsock = open('/var/log/fluxtwitter.log', 'w')
        sys.stdout = fsock
        sys.stderr = fsock

class OAuthApi(Api):
    "OAuthApi code from http://oauth-python-twitter.googlecode.com"
    def __init__(self, consumer_key, consumer_secret, access_token=None):
        if access_token:
            Api.__init__(self,access_token.key, access_token.secret)
        else:
            Api.__init__(self)
        self._Consumer = oauth.OAuthConsumer(consumer_key, consumer_secret)
        self._signature_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
        self._access_token = access_token


    def _GetOpener(self):
        opener = self._urllib.build_opener()
        return opener

    def _FetchUrl(self,
                    url,
                    post_data=None,
                    parameters=None,
                    no_cache=None):
        '''Fetch a URL, optionally caching for a specified time.

        Args:
          url: The URL to retrieve
          post_data:
            A dict of (str, unicode) key/value pairs.  If set, POST will be used.
          parameters:
            A dict whose key/value pairs should encoded and added
            to the query string. [OPTIONAL]
          no_cache: If true, overrides the cache on the current request

        Returns:
          A string containing the body of the response.
        '''
        # Build the extra parameters dict
        extra_params = {}
        if self._default_params:
          extra_params.update(self._default_params)
        if parameters:
          extra_params.update(parameters)

        # Add key/value parameters to the query string of the url
        #url = self._BuildUrl(url, extra_params=extra_params)

        if post_data:
            http_method = "POST"
            extra_params.update(post_data)
        else:
            http_method = "GET"

        req = self._makeOAuthRequest(url, parameters=extra_params,
                                                    http_method=http_method)
        self._signRequest(req, self._signature_method)


        # Get a url opener that can handle Oauth basic auth
        opener = self._GetOpener()

        #encoded_post_data = self._EncodePostData(post_data)

        if post_data:
            encoded_post_data = req.to_postdata()
            url = req.get_normalized_http_url()
        else:
            url = req.to_url()
            encoded_post_data = ""

        no_cache=True
        # Open and return the URL immediately if we're not going to cache
        # OR we are posting data
        if encoded_post_data or no_cache:
          if encoded_post_data:
              url_data = opener.open(url, encoded_post_data).read()
          else:
              url_data = opener.open(url).read()
          opener.close()
        else:
          # Unique keys are a combination of the url and the username
          if self._username:
            key = self._username + ':' + url
          else:
            key = url

          # See if it has been cached before
          last_cached = self._cache.GetCachedTime(key)

          # If the cached version is outdated then fetch another and store it
          if not last_cached or time.time() >= last_cached + self._cache_timeout:
            url_data = opener.open(url).read()
            opener.close()
            self._cache.Set(key, url_data)
          else:
            url_data = self._cache.Get(key)

        # Always return the latest version
        return url_data

    def _makeOAuthRequest(self, url, token=None,
                                        parameters=None, http_method="GET"):
        '''Make a OAuth request from url and parameters

        Args:
          url: The Url to use for creating OAuth Request
          parameters:
             The URL parameters
          http_method:
             The HTTP method to use
        Returns:
          A OAauthRequest object
        '''
        if not token:
            token = self._access_token
        request = oauth.OAuthRequest.from_consumer_and_token(
                            self._Consumer, token=token,
                            http_url=url, parameters=parameters,
                            http_method=http_method)
        return request

    def _signRequest(self, req, signature_method=oauth.OAuthSignatureMethod_HMAC_SHA1()):
        '''Sign a request

        Reminder: Created this function so incase
        if I need to add anything to request before signing

        Args:
          req: The OAuth request created via _makeOAuthRequest
          signate_method:
             The oauth signature method to use
        '''
        req.sign_request(signature_method, self._Consumer, self._access_token)


    def getAuthorizationURL(self, token, url=AUTHORIZATION_URL):
        '''Create a signed authorization URL

        Returns:
          A signed OAuthRequest authorization URL
        '''
        req = self._makeOAuthRequest(url, token=token)
        self._signRequest(req)
        return req.to_url()

    def getSigninURL(self, token, url=SIGNIN_URL):
        '''Create a signed Sign-in URL

        Returns:
          A signed OAuthRequest Sign-in URL
        '''

        signin_url = self.getAuthorizationURL(token, url)
        return signin_url

    def getAccessToken(self, pin, url=ACCESS_TOKEN_URL):
        token = self._FetchUrl(url, parameters={'oauth_verifier':pin},no_cache=True)
        return oauth.OAuthToken.from_string(token)

    def getRequestToken(self, url=REQUEST_TOKEN_URL):
        '''Get a Request Token from Twitter

        Returns:
          A OAuthToken object containing a request token
        '''
        resp = self._FetchUrl(url, no_cache=True)
        token = oauth.OAuthToken.from_string(resp)
        return token

    def GetUserInfo(self, url='https://twitter.com/account/verify_credentials.json'):
        '''Get user information from twitter

        Returns:
          Returns the twitter.User object
        '''
        json = self._FetchUrl(url)
        data = simplejson.loads(json)
        self._CheckForTwitterError(data)
        return User.NewFromJsonDict(data)


class TwitterStatusIcon(gtk.StatusIcon):
	def __init__(self):
		gtk.StatusIcon.__init__(self)
		
		# creating the status icon with its menu
		menu = '''
			<ui>
			 <menubar name="Twitter">
			  <menu action="Menu">
			   <menuitem action="Update"/>
                           <menuitem action="Settings"/>
			   <menuitem action="About"/>
			   <menuitem action="Close"/>
			  </menu>
			 </menubar>
			</ui>
		'''
		actions = [
			('Menu',  None, 'Menu'),
			('Update', gtk.STOCK_REFRESH, '_Update now', None, 'Update', self.update),
			('Settings', gtk.STOCK_PREFERENCES, '_Settings...', None, 'Settings', self.config),
			('About', gtk.STOCK_ABOUT, '_About...', None, 'About Fluxtwitter', self.about),
			('Close', gtk.STOCK_CLOSE, '_Close', None, 'Close', self.close)]
		ag = gtk.ActionGroup('Actions')
		ag.add_actions(actions)
		self.manager = gtk.UIManager()
		self.manager.insert_action_group(ag, 0)
		self.manager.add_ui_from_string(menu)
		self.menu = self.manager.get_widget('/Twitter/Menu/About').props.parent
		self.icon = gtk.gdk.pixbuf_new_from_xpm_data(fluxicon)
		self.iconnew = gtk.gdk.pixbuf_new_from_xpm_data(iconnew)
		self.set_from_pixbuf(self.icon)
		self.getconfig()
		self.set_visible(True)
		self.isTweet = False
		self.connect('popup-menu', self.popup_menu)
		self.connect('activate', self.showtimeline)
                self.api = OAuthApi(CONSUMERKEY, CONSUMERSECRET)
                self.request_token = self.api.getRequestToken()
                if not self.accesstoken:
                        self.getpin()
                else:
                        self.launch()

        def launch(self):
                # registrating
                self.api = OAuthApi(CONSUMERKEY, CONSUMERSECRET, self.accesstoken)
                self.username = self.api.GetUserInfo().name

		# creating the main dialog
                self.set_tooltip(self.username + "'s timeline")
		self.tweetdialog = gtk.Window()
		self.tweetdialog.connect("destroy",self.showtimeline)
		self.tweetdialog.connect("delete-event",self.showtimeline)
		self.tweetdialog.connect('configure-event', self.updateBackground)
		self.tweetdialog.set_title('twitter - '+self.username)
		self.tweetdialog.set_icon(self.icon)
		self.tweetdialog.set_border_width(5)
		self.tweetdialog.set_size_request(280, 500)
		self.layout = gtk.ScrolledWindow()
		self.layout.set_policy(gtk.POLICY_NEVER,gtk.POLICY_AUTOMATIC)
		self.vbox = gtk.VBox()
		self.layout.add_with_viewport(self.vbox)
		self.tweetdialog.add(self.layout)
		self.layout.get_child().set_shadow_type(gtk.SHADOW_NONE)
		self.layout.connect('scroll-child', self.updateBackground)
		self.tweets = []
		self.table = None
		self.iteration = 1
		self.updateBackground()
		self.timeout = gobject.timeout_add(self.interval*1000,self.update)
		self.update()

	def update(self, data=None):

		# updating from twitter
		print "iteration",self.iteration,": fetching",self.timeout,"tweets on",time.strftime('%X %x %Z')
		try:
			statuses = self.api.GetFriendsTimeline(count=self.displaytweets)
		except:
			print "Error: Couldn't connect to Twitter server."
			return True # even if we cannot connect, we continue trying next time
		self.iteration += 1
		extras = 0
		if (not self.tweets):
			extras = len(statuses)
			self.set_from_pixbuf(self.iconnew)
		elif (statuses[0].id != self.tweets[0]['id']):
			self.set_from_pixbuf(self.iconnew)
			for i in range(len(statuses)):
				if statuses[i].id == self.tweets[0]['id']:
					extras = i
					break
		if not extras:
			print "no new tweet to display"
			return True
		print 'list currently has',len(self.tweets),' - adding',extras
		
		for i in range(extras-1,-1,-1):

			# retrieving all we need from the tweet
			iconurl = statuses[i].user.GetProfileImageUrl()
			iconfile=urllib.urlopen(iconurl)
			print 'extra tweet',i,"from ",statuses[i].user.name," : ",statuses[i].text," ",iconurl
                        tweetpb = None
                        try:
                                pbl = gtk.gdk.PixbufLoader()
                                pbl.write(iconfile.read())
                                tweetpb = pbl.get_pixbuf()
                                pbl.close()
                        except:
                                print "error reading avatar file"
			if not tweetpb:
				# if icon is invalid, try to get a monsterid
				h = hashlib.md5()
				h.update(statuses[i].user.screen_name)
				v = h.hexdigest()
				url = "http://friedcellcollective.net/monsterid/"+v+"/48"
				iconfile=urllib.urlopen(url)
				pbl = gtk.gdk.PixbufLoader()
				pbl.write(iconfile.read())
				tweetpb = pbl.get_pixbuf()
				pbl.close()
			if not tweetpb:
				# if everything fails, use default icon
				tweetpb = self.icon
				
			tweetpb = tweetpb.scale_simple(48,48,gtk.gdk.INTERP_BILINEAR)	
			tweettext = statuses[i].text.replace('&ccedil;','c')
			tweettext = tweettext.replace('&atilde;','a')
			tweettext = tweettext.replace("'","")
			tweettext = tweettext.replace("&","&amp;")
			pat1 = re.compile(r"(^|[\n ])(([\w]+?://[\w\#$%&~.\-;:=,?@\[\]+]*)(/[\w\#$%&~/.\-;:=,?@\[\]+]*)?)", re.IGNORECASE | re.DOTALL)
			pat2 = re.compile(r"(^|[\n ])(@([\w\#$%&~.\-;:=,?@\[\]+]*)(/[\w\#$%&~/.\-;:=,?@\[\]+]*)?)", re.IGNORECASE | re.DOTALL)
			pat3 = re.compile(r"(^|[\n ])(#([\w\#$%&~.\-;:=,?@\[\]+]*)(/[\w\#$%&~/.\-;:=,?@\[\]+]*)?)", re.IGNORECASE | re.DOTALL)
			tweettext = pat1.sub(r'\1<a href="\2">\3</a>', tweettext)
			tweettext = pat2.sub(r'\1<a href="http://www.twitter.com/\3">\2</a>', tweettext)
			tweettext = pat3.sub(r'\1<a href="http://www.twitter.com/#search?q=%23\3">\2</a>', tweettext)
			# adding to our tweet list
			thistweet = {'id':statuses[i].id,
				     'user':statuses[i].user.screen_name,
				     'tweet':tweettext,
				     'icon':tweetpb}
			self.tweets.insert(0,thistweet) #adding our new tweet to the top of the list

		# if list window is visible, don't stack
		if self.isTweet: self.tweets = self.tweets[:self.displaytweets]

		# dont rebuild if window is open (buggy)
		# if not self.isTweet: self.rebuildTable()
                self.rebuildTable()
		return True

	def rebuildTable(self):
		print "building table with",len(self.tweets),"items"
		newtable = gtk.Table(len(self.tweets),2)
		newtable.set_row_spacings(10)
		for i in range(len(self.tweets)):
			label = gtk.Label()
			label.set_line_wrap(True)
			label.set_width_chars(25)
			label.set_markup(self.tweets[i]['tweet'])
			label.set_selectable(True)
			# label.connect("activate-current-link",self.clicked) # not really working
			newtable.attach(label,1,2,i,i+1)
			icon = gtk.Image()
			icon.set_from_pixbuf(self.tweets[i]['icon'])
			icon.set_tooltip_text(self.tweets[i]['user'])
			button = gtk.Button()
			button.set_relief(gtk.RELIEF_NONE)
			button.set_image(icon)
			button.set_name(str(i))
			button.connect("clicked",self.clicked)
			button.set_focus_on_click(False)
			newtable.attach(button,0,1,i,i+1)
		if self.table: self.vbox.remove(self.table)
		self.vbox.pack_start(newtable)
		self.table = newtable

	def getconfig(self):
		self.displaytweets = DISPLAYTWEETS
		self.browser = BROWSER
		self.interval = INTERVAL
		self.composite = COMPOSITE
		self.transparency = TRANSPARENCY
		self.toolbarheight = TOOLBARHEIGHT
		self.compositecolor = COMPOSITECOLOR
		self.stackmode = STACKMODE
                self.accesstoken = ACCESSTOKEN
		configfile = os.path.expanduser('~') + os.sep + '.fluxtwitterrc'
		if os.path.isfile(configfile):
                        print "reading config file"
			file = open(configfile)
			for line in file:
				if not("#" in line):
					key, value = line.split("=", 1)
					key = key.strip()
					value = value.strip()
					if key == "displaytweets": self.displaytweets = int(value)
					elif key == "browser": self.browser = value
					elif key == "interval": self.interval = int(value)
					elif key == "composite": self.composite = bool(int(value))
					elif key == "transparency": self.transparency = int(value)
					elif key == "toolbarheight": self.toolbarheight = int(value)
					elif key == "compositecolor": self.compositecolor = string.atoi(value,0)
					elif key == "stackmode": self.stackmode = bool(int(value))
                                        elif key == "accesstoken": self.accesstoken = oauth.OAuthToken.from_string(value)
			file.close()
		else:
			print "Creating config file..."
			self.writeconfig()

	def writeconfig(self):
		configfile = os.path.expanduser('~') + os.sep + '.fluxtwitterrc'
		file = open(configfile,'wb')
		file.write('# Fluxtwitter configuration file\n')
		file.write('# Number of tweets displayed (default 8)\n')
		file.write('displaytweets = ' + str(self.displaytweets) + '\n')
		file.write('# Browser command to open links (default x-www-browser) \n')
		file.write('browser = ' + self.browser + '\n')
		file.write('# Interval in seconds between twitter updates (default 120)\n')
		file.write('interval = ' + str(self.interval) + '\n')
		file.write('# Do we use pseudo-transparency?\n')
		file.write('composite = '+ str(int(self.composite)) + '\n')
		file.write('# Amount of image fading in percent\n')
		file.write('transparency = '+ str(self.transparency) + '\n')
		file.write('# Color to composite background with (0x00000000)\n')
		file.write('compositecolor = '+str(self.compositecolor) + '\n')
		file.write('# Window titlebar height correction in pixels\n')
		file.write('toolbarheight = ' + str(self.toolbarheight) + '\n')
		file.write('# Stack mode (if tweets will stack until you read them\n')
		file.write('stackmode = ' + str(int(self.stackmode)) + '\n')
                if self.accesstoken:
                        file.write('# Access token (automatically generated once you allow it on twitter\n')
                        file.write('accesstoken = ' + self.accesstoken.to_string() + '\n')
		file.close()

	def config(self,data):
		dialog = gtk.Dialog()
		dialog.set_title('Fluxtwitter settings')
		table = gtk.Table(8,2)
		c1 = gtk.Entry()
		c1.set_text(str(self.displaytweets))
		c1.set_tooltip_text('Number of tweets to display')
		c2 = gtk.Entry()
		c2.set_text(self.browser)
		c2.set_tooltip_text('Web browser to open links in')
		c3 = gtk.Entry()
		c3.set_text(str(self.interval))
		c3.set_tooltip_text('Interval in seconds between updates')
		c4 = gtk.ToggleButton()
		c4.set_active(self.composite)
		c4.set_tooltip_text('Check this to use fluxbox pseudo-transparency')
		c5 = gtk.Entry()
		c5.set_text(str(self.transparency))
		c5.set_tooltip_text('Fading level in percents')
		c6 = gtk.Entry()
		c6.set_text(str(self.toolbarheight))
		c6.set_tooltip_text('Vertical correction in pixels')
		c7 = gtk.Entry()
		c7.set_text(str(self.compositecolor))
		c7.set_tooltip_text('Composite color for transparency')
		c8 = gtk.ToggleButton()
		c8.set_active(self.stackmode)
		c8.set_tooltip_text('Check this for tweets to stack until you read them')
		table.attach(gtk.Label('Nr of tweets '),0,1,0,1)
		table.attach(c1,1,2,0,1)
		table.attach(gtk.Label('Web browser '),0,1,1,2)
		table.attach(c2,1,2,1,2)
		table.attach(gtk.Label('Interval '),0,1,2,3)
		table.attach(c3,1,2,2,3)
		table.attach(gtk.Label('Pseudo-transparency '),0,1,3,4)
		table.attach(c4,1,2,3,4)
		table.attach(gtk.Label('Fading '),0,1,4,5)
		table.attach(c5,1,2,4,5)
		table.attach(gtk.Label('Vertical correction '),0,1,5,6)
		table.attach(c6,1,2,5,6)
		table.attach(gtk.Label('Composite Color '),0,1,6,7)
		table.attach(c7,1,2,6,7)
		table.attach(gtk.Label('Stack mode '),0,1,7,8)
		table.attach(c8,1,2,7,8)
		dialog.vbox.pack_start(table)
		dialog.show_all()
		cancel_button = dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
		ok_button = dialog.add_button(gtk.STOCK_OK,gtk.RESPONSE_OK)
		ok_button.grab_default()
		resp = dialog.run()
		if resp == gtk.RESPONSE_OK:
			self.displaytweets = int(c1.get_text())
			self.browser = c2.get_text()
			self.interval = int(c3.get_text())
			self.composite = c4.get_active()
			self.transparency = int(c5.get_text())
			self.toolbarheight = int(c6.get_text())
			self.compositecolor = string.atoi(c7.get_text(),0)
			self.stackmode = c8.get_active()
			self.writeconfig()
		dialog.destroy()

        def getpin(self):
                auth_url = self.api.getAuthorizationURL(self.request_token)
                subprocess.Popen([self.browser,auth_url],shell=False)
		dialog = gtk.Dialog()
		dialog.set_title('Inform Twitter authorization PIN')
		table = gtk.Table(2,1)
		c1 = gtk.Entry()
		c1.set_tooltip_text('The PIN number you received from twitter')
		table.attach(gtk.Label('Twitter PIN '),0,1,0,1)
		table.attach(c1,1,2,0,1)
		dialog.vbox.pack_start(table)
		dialog.show_all()
		cancel_button = dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
		ok_button = dialog.add_button(gtk.STOCK_OK,gtk.RESPONSE_OK)
		ok_button.grab_default()
		resp = dialog.run()
		if resp == gtk.RESPONSE_OK:
			pin = c1.get_text()
                        dialog.destroy()
                        self.api = OAuthApi(CONSUMERKEY, CONSUMERSECRET, self.request_token)
                        self.accesstoken = self.api.getAccessToken(pin)
                        self.writeconfig()
                        self.launch()


	def updateBackground(self,args=None,stuff=None):
		if self.composite:
                        print "rebuilding background"
			x,y = self.tweetdialog.get_position()
			w,h = self.tweetdialog.get_size()
			bgfile = os.path.expanduser('~') + os.sep + '.fluxbox/lastwallpaper'
			if os.path.isfile(bgfile):
				wpfile = open(bgfile)
				pb=gtk.gdk.pixbuf_new_from_file(wpfile.read().split('|')[1])
				wpfile.close()
				crop = gtk.gdk.Pixbuf( gtk.gdk.COLORSPACE_RGB, False, 8, w, h )
				pb.copy_area(x, y+self.toolbarheight, w, h, crop, 0, 0)
				mask = crop.copy()
				mask.fill(self.compositecolor)
				opacity = int((self.transparency/100.0)*255)
				mask.composite(crop, 0, 0, w, h, 0, 0, 1, 1, gtk.gdk.INTERP_BILINEAR, opacity)
				pm,m = crop.render_pixmap_and_mask(255)
				style = self.tweetdialog.get_style().copy()
				style.bg_pixmap[gtk.STATE_NORMAL] = pm
				self.tweetdialog.set_style(style)
				self.layout.get_child().set_style(style)

	def clicked(self,data,url=None):
		if data.name:
			url="http://www.twitter.com/"+self.tweets[int(data.name)]['user']
		print "clicked link:",url
		self.tweetdialog.hide()
		self.isTweet = False
		self.tweets = self.tweets[:self.displaytweets]
		self.rebuildTable()
		subprocess.Popen([self.browser,url],shell=False)

	def close(self, data):
		gobject.source_remove(self.timeout)
		gtk.main_quit()

	def popup_menu(self, status, button, time):
		self.menu.popup(None, None, None, button, time)

	def about(self, data):
		dialog = gtk.AboutDialog()
		dialog.set_name('Fluxtwitter')
		dialog.set_version('0.2')
		dialog.set_comments('A system tray icon displaying twitter feed')
		dialog.set_website('http://yorik.uncreated.net')
		dialog.run()
		dialog.destroy()

	def showtimeline(self,data,event=None):
		if self.isTweet:
			self.tweetdialog.hide()
			self.isTweet = False
			self.tweets = self.tweets[:self.displaytweets]
			self.rebuildTable()
		else:
			self.isTweet = True
			self.tweetdialog.show_all()
			self.set_from_pixbuf(self.icon)
		return True

if __name__ == '__main__':
        if len(sys.argv) == 1:
                # no argument? GUI mode
                TwitterStatusIcon()
                gtk.main()
        else:
                try:
                        opts, args = getopt.getopt(sys.argv[1:], "th", ["text","help"])
                except getopt.GetoptError:
                        print "Unrecognized option."
                        print __doc__
                        sys.exit()
                else:
                        for o, a in opts:
                                if o in ("-t", "--text"):
                                        # with -t or --text? we output the last 5 tweets
                                        accesstoken = ACCESSTOKEN
                                        configfile = os.path.expanduser('~') + os.sep + '.fluxtwitterrc'
                                        if os.path.isfile(configfile):
                                                file = open(configfile)
                                                for line in file:
                                                        if not("#" in line):
                                                                key, value = line.split("=", 1)
                                                                key = key.strip()
                                                                value = value.strip()
                                                                if key == "accesstoken":
                                                                        accesstoken = oauth.OAuthToken.from_string(value)
                                                file.close()
                                                api = OAuthApi(CONSUMERKEY, CONSUMERSECRET)
                                                request_token = api.getRequestToken()
                                                api = OAuthApi(CONSUMERKEY, CONSUMERSECRET, accesstoken)
                                                statuses = api.GetFriendsTimeline(count=5)
                                                for s in statuses:
                                                        print s.user.name + " : " + s.text
                                if o in ("-h", "--help"):
                                       print __doc__
                                       sys.exit()
