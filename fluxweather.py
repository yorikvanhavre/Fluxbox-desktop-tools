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

__title__='Fluxweather'
__author__='Yorik van Have'
__url__='http://yorik.uncreated.net'
__version__='0.6.0 - 15.11.2010'

'''
This program adds an icon in the system tray  displaying weather conditions 
and forecast from yahoo.com. I made this primarily for fluxbox and other 
window managers that don't have a weather icon embedded in the clock.  
'''

import os, gtk, gobject, urllib, getopt, sys
from xml.etree.ElementTree import parse

# DEFAULT CONFIGURATION - OVERRIDDEN BY CONFIG FILE .fluxweatherrc IN YOUR HOME DIR
# NORMALLY, YOU DON'T NEED TO TOUCH ANYTHING BELOW (EVERYTHING IS DONE VIA THE SETTINGS
# MENU).

# below are the yahoo weather URLs, normaly you don't need to change that
WEATHER_URL = 'http://xml.weather.yahoo.com/forecastrss?p=%s&u=c'
WEATHER_NS = 'http://xml.weather.yahoo.com/ns/rss/1.0'
# below is your zip code, or the code corresponding to your location
# from http://weather.yahoo.com
ZIPCODE = 'BRXX0232'
# below is the url of a weather map image to fetch, get it from same yahoo page.
MAPURL='http://weather.yahoo.com/images/sa_satintl_440_mdy_y.jpg'
# below is the number of animated images. 0 means no animation
ANIM = 5
# END CONFIGURATION

AnimatedMapUrl1='http://image.weather.com/looper/archive/brazil_sat_277x187/#L.jpg'
AnimatedMapUrl2='http://www4.climatempo.com.br/mapas/satelite/g12/br/br4Kbm#.jpg'
HELPMSG = '''fluxweather [OPTIONS] : runs the fluxeather system tray app, or
displays temperature or forecast information.

available options:
    -t or --temp:      displays current temperature in centigrade degrees
    -r or --readtemp:  reads last fetched temperature from disk
    -c or --condition: displays the current weather condition and temperature
    -p or --prevision: displays a prevision for the next day
                       (condition + temperature)
                              '''

def fetchweather(zip=ZIPCODE):
    url = WEATHER_URL % zip
    rss = parse(urllib.urlopen(url)).getroot()
    forecasts = []
    for element in rss.findall('channel/item/{%s}forecast' % WEATHER_NS):
        forecasts.append({
            'date': element.get('date'),
            'low': element.get('low'),
            'high': element.get('high'),
            'condition': element.get('text')
        })
    ycondition = rss.find('channel/item/{%s}condition' % WEATHER_NS)
    return {
        'current_condition': ycondition.get('text'),
        'current_temp': ycondition.get('temp'),
        'forecasts': forecasts,
        'title': rss.findtext('channel/title'),
        'code': ycondition.get('code'),
        'descr': rss.findtext('channel/item/description')
        }

def getZipCode():
    configfile = os.path.expanduser('~') + os.sep + '.fluxweatherrc'
    zipcode = ZIPCODE
    if os.path.isfile(configfile):
        file = open(configfile)
        for line in file:
            if not(line[0] == '#'):
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key == "zipcode": zipcode = value
    return zipcode

def getPixBuf(report=fetchweather()):
    iconurl=report['descr'].split('"')[1]
    iconfile=urllib.urlopen(iconurl)
    pbl = gtk.gdk.PixbufLoader()
    pbl.write(iconfile.read())
    pb = pbl.get_pixbuf()
    pbl.close()
    return pb

def getToolTip(report=fetchweather()):
    forecasts = report['forecasts']
    panel = report['title'] + '\n'+report['current_temp'] + '\260C ' + report['current_condition'] + '\n'
    panel = panel + 'tomorrow: ' + forecasts[0]['low'] + '/' + forecasts[0]['high'] 
    panel = panel + '\260C ' + forecasts[0]['condition'] + '\n'
    panel = panel + 'day after: ' + forecasts[1]['low'] + '/' + forecasts[1]['high'] 
    panel = panel + '\260C ' + forecasts[1]['condition']
    panel = unicode(panel,'latin1')
    return panel

def getTemp():
    "reads temperature from temp file"
    t = ''
    if os.path.isfile(os.path.expanduser('~') + os.sep + '.temperature'):
        fil = open(os.path.expanduser('~') + os.sep + '.temperature')
        for line in fil:
            t = line
        fil.close()
    return t

class TrackerStatusIcon(gtk.StatusIcon):
    def __init__(self):
        gtk.StatusIcon.__init__(self)
        menu = '''
            <ui>
             <menubar name="Weath">
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
            ('About', gtk.STOCK_ABOUT, '_About...', None, 'About Weath', self.about),
            ('Close', gtk.STOCK_CLOSE, '_Close', None, 'Close', self.close)]
        ag = gtk.ActionGroup('Actions')
        ag.add_actions(actions)
        self.manager = gtk.UIManager()
        self.manager.insert_action_group(ag, 0)
        self.manager.add_ui_from_string(menu)
        self.menu = self.manager.get_widget('/Weath/Menu/About').props.parent
        self.set_from_stock(gtk.STOCK_CONNECT)
        self.set_tooltip('Connecting...')
        self.set_visible(True)
        self.isMap = False
        self.connect('popup-menu', self.popup_menu)
        self.connect('activate', self.map)
        self.mapdialog = gtk.Window()
        self.mapdialog.connect("destroy",self.map)
        self.mapdialog.connect("delete-event",self.map)
        self.getconfig()
        self.update()
        self.satimage = gtk.Image()
        if self.animated:
            self.satpb = self.images[0]
        self.satimage.set_from_pixbuf(self.satpb)
        self.mapdialog.add(self.satimage)
        self.animatedNr = 0
        self.stopanim = False
        self.timeout  = gobject.timeout_add(3600000,self.update)

    def update(self, data=None):
        report = fetchweather(self.zip)
        self.set_tooltip(getToolTip(report))
        self.set_from_pixbuf(getPixBuf(report))
        if not self.animated:
            imfile=urllib.urlopen(self.map)
            pbl = gtk.gdk.PixbufLoader()
            pbl.write(imfile.read())
            pb = pbl.get_pixbuf()
            pbl.close()
            self.satpb = pb
        else:
            self.images = []
            for i in range(self.animated):
                url = self.map.replace('#',str(i+1))
                imfile=urllib.urlopen(url)
                pbl = gtk.gdk.PixbufLoader()
                pbl.write(imfile.read())
                pb = pbl.get_pixbuf()
                pbl.close()
                self.images.append(pb)
        self.writeTemp(report['current_temp'])
        return True

    def getconfig(self):
        configfile = os.path.expanduser('~') + os.sep + '.fluxweatherrc'
        self.zip = ZIPCODE
        self.map = MAPURL
        self.animated = ANIM
        if os.path.isfile(configfile):
            file = open(configfile)
            for line in file:
                if not(line[0] == '#'):
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if key == "zipcode": self.zip = value
                    elif key == "mapurl": self.map = value
                    elif key == "animated": self.animated = int(value)
            file.close()
        else:
            print "Creating config file..."
            self.writeconfig()

    def writeconfig(self):
        configfile = os.path.expanduser('~') + os.sep + '.fluxweatherrc'
        file = open(configfile,'wb')
        file.write('# Fluxweather configuration file\n')
        file.write('# This is the zip or location code from http://weather.yahoo.com\n')
        file.write('zipcode = ' + self.zip + '\n')
        file.write('# This is the url of a satellite image you want to display when\n')
        file.write('# left-clicking the fluxweather icon\n')
        file.write('mapurl = ' + self.map + '\n')
        file.write('# if animated = 0, the map image above is not animated. If it is\n')
        file.write('# another number, any "#" character in the url above will be changed\n')
        file.write('# by a number from 1 to the given number, making the map animated.\n')
        file.write('animated = ' + str(self.animated) + '\n')
        file.close()

    def writeTemp(self,temp):
        "writes the temperature to a temp file"
        fil = open(os.path.expanduser('~') + os.sep + '.temperature','wb')
        fil.write(str(temp))
        fil.close()

    def close(self, data):
        gtk.timeout_remove(self.timeout)
        gtk.main_quit()

    def popup_menu(self, status, button, time):
        self.menu.popup(None, None, None, button, time)

    def about(self, data):
        dialog = gtk.AboutDialog()
        dialog.set_name(__title__)
        dialog.set_version(__version__)
        dialog.set_comments(__doc__)
        dialog.set_website(__url__)
        dialog.run()
        dialog.destroy()

    def config(self,data):
        dialog = gtk.Dialog()
        dialog.set_name('Fluxweather settings')
        table = gtk.Table(3,2)
        cfzip = gtk.Entry()
        cfzip.set_text(self.zip)
        cfzip.set_tooltip_text('Your Location code from  http://weather.yahoo.com')
        cfmap = gtk.Entry()
        cfmap.set_text(self.map)
        cfmap.set_tooltip_text('The URL of a satellite image. Use # for animated number.')
        cfanim = gtk.Entry()
        cfanim.set_text(str(self.animated))
        cfanim.set_tooltip_text('The number of animated frames in the URL above')
        table.attach(gtk.Label('Zipcode '),0,1,0,1)
        table.attach(cfzip,1,2,0,1)
        table.attach(gtk.Label('Map Url '),0,1,1,2)
        table.attach(cfmap,1,2,1,2)
        table.attach(gtk.Label('Frames '),0,1,2,3)
        table.attach(cfanim,1,2,2,3)
        dialog.vbox.pack_start(table)
        dialog.show_all()
        cancel_button = dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        ok_button = dialog.add_button(gtk.STOCK_OK,gtk.RESPONSE_OK)
        ok_button.grab_default()
        resp = dialog.run()
        if resp == gtk.RESPONSE_OK:
            self.zip = cfzip.get_text()
            self.map = cfmap.get_text()
            self.animated = int(cfanim.get_text())
            self.writeconfig()
        dialog.destroy()

    def map(self,data,otherstuff=None):
        if self.isMap:
            self.mapdialog.hide()
            if self.animated: self.stopanim = True
            self.isMap = False
        else:
            self.isMap = True
            if self.animated:
                self.maptimeout  = gobject.timeout_add(500,self.animateMap)
            self.mapdialog.show_all()

    def animateMap(self):
        if self.stopanim:
            self.stopanim = False
            return False
        if self.animatedNr == self.animated:
            self.animatedNr = 0
        self.satimage.set_from_pixbuf(self.images[self.animatedNr])
        self.animatedNr += 1
        return True
            
if __name__ == '__main__':
    if len(sys.argv) == 1:
        # no argument? GUI mode
        TrackerStatusIcon()
        gtk.main()
    else:
        try:
            opts, args = getopt.getopt(sys.argv[1:], "trcp", ["temp","readtemp","condition","prevision"])
        except getopt.GetoptError:
            print HELPMSG
            sys.exit()
        else:
            for o, a in opts:
                if o in ("-t", "--temp"):
                    # current temp
                    report = fetchweather(getZipCode())
                    print report['current_temp']
                elif o in ("-r", "--readtemp"):
                    # current temp   
                    print getTemp()
                elif o in ("-c", "--condition"):
                    # current condition
                    report = fetchweather(getZipCode())
                    print report['current_condition'] + " " + report['current_temp']
                elif o in ("-p", "--prevision"):
                    # fetching prevision
                    report = fetchweather(getZipCode())
                    forecasts = report['forecasts']
                    print forecasts[0]['condition'] + " " + forecasts[0]['low'] + '/' + forecasts[0]['high'] 
                

