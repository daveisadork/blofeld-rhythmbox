import rhythmdb, rb
import gobject, gtk
import gnome, gconf
import urlparse
import anyjson
import datetime

# the gconf configuration
gconf_keys = {
    'address': "/apps/rhythmbox/plugins/blofeld/address",
    'username': "/apps/rhythmbox/plugins/blofeld/username",
    'password': "/apps/rhythmbox/plugins/blofeld/password",
}


class Blofeld(rb.Plugin):


    def __init__(self):
        self.source = None
        rb.Plugin.__init__(self)
        self.config = gconf.client_get_default()

        if self.config.get(gconf_keys['address']) is None:
            # key not yet found represented by "None"
            self._set_defaults()

    def _set_defaults(self):
        self.config.set_string(gconf_keys['address'], 'http://localhost:8083')
        self.config.set_string(gconf_keys['username'], '')
        self.config.set_string(gconf_keys['password'], '')

    def activate(self, shell):
        self.db = shell.get_property("db")
        self.entry_type = self.db.entry_register_type("BlofeldEntryType")
        model = self.db.query_model_new_empty()
        group = rb.rb_source_group_get_by_name ("library")
        if not group:
            group = rb.rb_source_group_register ("library",
                _("Library"),
                rb.SOURCE_GROUP_CATEGORY_FIXED)
        theme = gtk.icon_theme_get_default()
        rb.append_plugin_source_path(theme, "/icons")

        width, height = gtk.icon_size_lookup(gtk.ICON_SIZE_LARGE_TOOLBAR)
        icon = rb.try_load_icon(theme, "network-server", width, 0)
        self.source = gobject.new (BlofeldSource,
                        shell=shell,
                        entry_type=self.entry_type,
                        source_group=group,
                        icon=icon,
                        plugin=self)
        shell.register_entry_type_for_source(self.source, self.entry_type)
        shell.append_source(self.source, None) # Add the source to the lis
        self.pec_id = shell.get_player().connect('playing-song-changed', self.playing_entry_changed)

    def deactivate(self, shell):
        print "deactivating sample python plugin"
        self.source.delete_thyself()
        self.source = None

    def playing_entry_changed (self, sp, entry):
        if self.source:
            self.source.playing_entry_changed (entry)
    
    def create_configure_dialog(self, dialog=None):
        if dialog is None:

            def store_config(dialog,address,username,password):
                address = address_entry.get_text()
                self.config.set_string(gconf_keys['address'],address)
                username = username_entry.get_text()
                self.config.set_string(gconf_keys['username'],username)
                password = password_entry.get_text()
                self.config.set_string(gconf_keys['password'],password)
                dialog.hide()

            dialog = gtk.Dialog(title='Blofeld Configuration',
                            parent=None,flags=0,buttons=None)
            dialog.set_default_size(400,350)

            table = gtk.Table(rows=3, columns=2, homogeneous=True)
            dialog.vbox.pack_start(table, False, False, 0)

            label = gtk.Label("Address :")
            label.set_alignment(0,0.5)
            table.attach(label, 0, 1, 0, 1)
            address_entry = gtk.Entry()
#            address_entry.set_max_length(16)
            if self.config.get_string(gconf_keys['address']) != None:
                address_entry.set_text(self.config.get_string(gconf_keys['address']))
            else:
                address_entry.set_text('')
            table.attach(address_entry, 1, 2, 0, 1,
                         xoptions=gtk.FILL|gtk.EXPAND,yoptions=gtk.FILL|gtk.EXPAND,xpadding=5,ypadding=5)

            label = gtk.Label("Username :")
            label.set_alignment(0,0.5)
            table.attach(label, 0, 1, 1, 2)
            username_entry = gtk.Entry()
#            address_entry.set_max_length(16)
            if self.config.get_string(gconf_keys['username']) != None:
                username_entry.set_text(self.config.get_string(gconf_keys['username']))
            else:
                username_entry.set_text('')
            table.attach(username_entry, 1, 2, 1, 2,
                         xoptions=gtk.FILL|gtk.EXPAND,yoptions=gtk.FILL|gtk.EXPAND,xpadding=5,ypadding=5)
                         
            label = gtk.Label("Password :")
            label.set_alignment(0,0.5)
            table.attach(label, 0, 1, 2, 3)
            password_entry = gtk.Entry()
#            address_entry.set_max_length(16)
            if self.config.get_string(gconf_keys['password']) != None:
                password_entry.set_text(self.config.get_string(gconf_keys['password']))
            else:
                password_entry.set_text('')
            table.attach(password_entry, 1, 2, 2, 3,
                         xoptions=gtk.FILL|gtk.EXPAND,yoptions=gtk.FILL|gtk.EXPAND,xpadding=5,ypadding=5)

            button = gtk.Button(stock=gtk.STOCK_CANCEL)
            dialog.action_area.pack_start(button, True, True, 5)
            button.connect("clicked", lambda w: dialog.hide())
            button = gtk.Button(stock=gtk.STOCK_OK)
            button.connect("clicked", lambda w: store_config(dialog,address_entry,username_entry,password_entry))
            dialog.action_area.pack_start(button, True, True, 5)
            dialog.show_all()


        dialog.present()
        return dialog


class BlofeldSource(rb.BrowserSource):
    __gproperties__ = {
        'plugin': (rb.Plugin, 'plugin', 'plugin', gobject.PARAM_WRITABLE|gobject.PARAM_CONSTRUCT_ONLY),
    }

    def __init__(self):
        rb.BrowserSource.__init__(self, name=_("Blofeld"))
        self.__db = None
        self.__activated = False
        self.__updating = False
        self.config = gconf.client_get_default()


    def do_impl_activate(self):
        if not self.__activated:
            shell = self.get_property('shell')
            self.__db = shell.get_property('db')
            self.__entry_type = self.get_property('entry-type')
            self.__activated = True
            self.__loaded = False
            self.__address = self.config.get_string(gconf_keys['address'])
        rb.BrowserSource.do_impl_activate (self)
        if (not self.__updating and not self.__loaded) or self.__address != self.config.get_string(gconf_keys['address']):
            self.__db.entry_delete_by_type(self.__entry_type)
            self.__load_total_size = 0
            (scheme, netloc,  path, query,
                                fragment) = urlparse.urlsplit(self.config.get_string(gconf_keys['address']))
            netloc = "%s:%s@%s" % (self.config.get_string(gconf_keys['username']), self.config.get_string(gconf_keys['password']), netloc)
            self.url = urlparse.urlunsplit((scheme, netloc, path, query, fragment))
            self.download_song_list()


    def download_song_list(self):
        loader = rb.Loader()
        self.__updating = True
        loader.get_url(self.url + '/list_songs?list_all=true', self.parse_song_list)


    def parse_song_list(self, song_list):
        self.songs = anyjson.deserialize(song_list)['songs']
        self.__load_total_size = len(self.songs)
        self.__load_current_size = len(self.songs)
        self.trackurl = self.url + '/get_song?songid='
        gobject.idle_add(self.add_song)

    def add_song(self):
        gtk.gdk.threads_enter()
        for x in range(100):
            if not self.songs:
                break
            song = self.songs.pop(0)
            entry = self.__db.entry_lookup_by_location (self.trackurl + song['id'])
            if entry == None:
                entry = self.__db.entry_new(self.__entry_type, self.trackurl + song['id'])
            self.__db.set(entry, rhythmdb.PROP_ARTIST, song['artist'])
            self.__db.set(entry, rhythmdb.PROP_ALBUM, song['album'])
            self.__db.set(entry, rhythmdb.PROP_TITLE, song['title'])
            self.__db.set(entry, rhythmdb.PROP_TRACK_NUMBER, song['tracknumber'])
            try:
                self.__db.set(entry, rhythmdb.PROP_BITRATE, song['bitrate'] / 1000)
            except:
                pass
            try:
                year = int(song['date'][0:4])
                date = datetime.date(year, 1, 1).toordinal()
                self.__db.set(entry, rhythmdb.PROP_DATE, date)
            except:
                pass
            try:
                self.__db.set(entry, rhythmdb.PROP_GENRE, ", ".join(song['genre']))
            except:
                self.__db.set(entry, rhythmdb.PROP_GENRE, "Unknown")
            try:
                self.__db.set(entry, rhythmdb.PROP_DURATION, int(round(song['length'])))
            except:
                pass
            self.__db.commit()
            x += 1
        self.__load_current_size = len(self.songs)
        gtk.gdk.threads_leave()
        if not self.songs:
            self.__updating = False
            self.__loaded = True
            return False
        return True

    def playing_entry_changed (self, entry):
        if not self.__db or not entry:
            return False
        if entry.get_entry_type() != self.__entry_type:
            return False
        gobject.idle_add (self.emit_cover_art_uri, entry)
        return True

    def emit_cover_art_uri (self, entry):
        url = self.__db.entry_get(entry, rhythmdb.PROP_LOCATION).replace('song?', 'cover?size=500&')
        self.__db.emit_entry_extra_metadata_notify (entry, 'rb:coverArt-uri', url)
        return False

    def do_impl_get_status(self):
        if self.__updating:
            if self.__load_total_size > 0:
                progress = min (float(self.__load_total_size - self.__load_current_size) / self.__load_total_size, 1.0)
            else:
                progress = -1.0
            return (_("Loading Blofeld library"), None, progress)
        else:
            qm = self.get_property("query-model")
            return (qm.compute_status_normal("%d song", "%d songs"), None, None)

    def do_set_property(self, property, value):
        if property.name == 'plugin':
            self.__plugin = value
        else:
            raise AttributeError, 'unknown property %s' % property.name

    def do_impl_get_browser_key (self):
        return "/apps/rhythmbox/plugins/blofeld/show_browser"

    def do_impl_get_paned_key (self):
        return "/apps/rhythmbox/plugins/blofeld/paned_position"



gobject.type_register(BlofeldSource)
