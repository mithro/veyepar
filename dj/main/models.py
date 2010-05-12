# models.py

from django.db import models
import os
import datetime

def fnify(text):
    """
    file_name_ify - make a file name out of text, like a talk title.
    convert spaces to _, remove junk like # and quotes.
    like slugify, but more file name friendly.
    """
    fn = text.replace(' ','_')
    fn = ''.join([c for c in fn if c.isalpha() or c.isdigit() or (c in '_') ])
    return fn

class Client(models.Model):
    sequence = models.IntegerField(default=1)
    active = models.BooleanField(help_text="Done for now.")
    name = models.CharField(max_length=135)
    slug = models.CharField(max_length=135,help_text="dir name to store input files")
    tags = models.TextField(null=True,blank=True,)
    description = models.TextField(blank=True)
    preroll = models.CharField(max_length=135, blank=True, 
        help_text="name of video to prepend")
    postroll = models.CharField(max_length=135, blank=True,
        help_text="name of video to postpend")
    blip_acct_name = models.CharField(max_length=30, blank=True, )
    def __unicode__(self):
        return self.name
    class Meta:
        ordering = ["sequence"]

class Location(models.Model):
    sequence = models.IntegerField(default=1)
    name = models.CharField(max_length=135,help_text="room name")
    slug = models.CharField(max_length=135,help_text="dir name to store input files")
    description = models.TextField(blank=True)
    def __unicode__(self):
        return "%s" % ( self.name )
    class Meta:
        ordering = ["sequence"]

class Show(models.Model):
    client = models.ForeignKey(Client)
    locations = models.ManyToManyField(Location)
    sequence = models.IntegerField(default=1)
    name = models.CharField(max_length=135)
    slug = models.CharField(max_length=135,help_text="dir name to store input files")
    tags = models.TextField(null=True,blank=True,)
    description = models.TextField(blank=True)
    @property
    def client_name(self):
        return self.client
    def __unicode__(self):
        return "%s: %s" % ( self.client_name, self.name )
    class Meta:
        ordering = ["sequence"]

class Raw_File(models.Model):
    location = models.ForeignKey(Location)
    show = models.ForeignKey(Show)
    filename = models.CharField(max_length=135,help_text="filename.dv")
    start = models.DateTimeField(null=True, blank=True, 
        help_text='when recorded (should agree with file name and timestamp)')
    duration = models.IntegerField(null=True,blank=True,)
    end = models.DateTimeField(null=True, blank=True)
    trash = models.BooleanField(help_text="This clip is trash")
    ocrtext = models.TextField(null=True,blank=True)
    comment = models.TextField(blank=True)
    def basename(self):
        return os.path.splitext(self.filename)[0]
    def durationhms(self):
        """ returns the lenth in h:m """
        duration = self.duration()
        hours = duration / 60
        minutes = duration - hours*60
        return "%02d:%02d" % (hours, minutes, )
    durationhms.short_description = 'Duration (h:m)'
    def __unicode__(self):
        return self.filename

    class Meta:
        ordering = ["filename"]


class Quality(models.Model):
    level = models.IntegerField()
    name = models.CharField(max_length=35)
    description = models.TextField(blank=True)
    def __unicode__(self):
        return self.name

STATES=((-2,'no flv'),(-1,'special'),(1,'edit'),(2,'encode'),(3,'review'),(4,'post',),(5,'tweet'),(6,'flac'),(7,'mv4'),(8,'flv?'),(9,'done'))
class Episode(models.Model):
    show = models.ForeignKey(Show)
    location = models.ForeignKey(Location, null=True)
    state = models.IntegerField(null=True,blank=True,choices=STATES,
        help_text="2=ready to encode, 4=ready to post, 5=tweet" )
    locked = models.DateTimeField(null=True, blank=True)
    locked_by = models.CharField(max_length=35, blank=True,
	 help_text="user/process that locked." )
    sequence = models.IntegerField(null=True,blank=True,
        help_text="process order")
    name = models.CharField(max_length=135, help_text="(synced from primary source)")
    slug = models.CharField(max_length=135,help_text="used for file name")
    released = models.NullBooleanField(null=True,blank=True,)
    primary = models.CharField(max_length=135,blank=True,
        help_text="pointer to master version of event (name,desc,time,author,files,etc)")
    authors = models.TextField(null=True,blank=True,)
    description = models.TextField(blank=True, help_text="(synced from primary source)")
    tags = models.CharField(max_length=135,null=True,blank=True,)
    normalise = models.CharField(max_length=5,null=True,blank=True, )

    channelcopy = models.CharField(max_length=2,null=True,blank=True,
          help_text='copy left to right (10) or right to left (01)' )
    license = models.IntegerField(null=True,blank=True,default=13)
    hidden = models.NullBooleanField(null=True,blank=True)
    thumbnail = models.CharField(max_length=135,null=True,blank=True, 
        help_text="filename.png" )
    target = models.CharField(max_length=135, null=True,blank=True,
        help_text = "Blip.tv episode ID")
    start = models.DateTimeField(blank=True, 
        help_text="initially scheduled time from master, adjusted to match reality")
    duration = models.IntegerField(null=True,blank=True,
        help_text="Lenght in minutes")
    video_quality = models.ForeignKey(Quality,null=True,blank=True,related_name='video_quality')
    audio_quality = models.ForeignKey(Quality,null=True,blank=True,related_name='audio_quality')
    comment = models.TextField(blank=True, help_text="production notes")
    def end(self):
       if self.start and self.duration:
           ret = self.start + datetime.timedelta(self.duration)
       else:
           ret = None
       return ret
           
    def __unicode__(self):
        return "%s: %s" % ( self.location.name, self.name )
    class Meta:
        ordering = ["sequence"]

class Cut_List(models.Model):
    raw_file = models.ForeignKey(Raw_File)
    episode = models.ForeignKey(Episode)
    sequence = models.IntegerField(default=1)
    start = models.CharField(max_length=11, blank=True, 
        help_text='offset from start in HH:MM:SS.SS')
    end = models.CharField(max_length=11, blank=True,
        help_text='offset from start in HH:MM:SS.SS')
    apply = models.BooleanField(default=1)
    comment = models.TextField(blank=True)
    def __unicode__(self):
        return "%s - %s" % (self.raw_file, self.episode)
    class Meta:
        ordering = ["sequence"]
    

class State(models.Model):
    sequence = models.IntegerField(default=1)
    slug = models.CharField(max_length=30)
    description = models.CharField(max_length=135, blank=True)

class Log(models.Model):
    episode = models.ForeignKey(Episode)
    state = models.ForeignKey(State, null=True, blank=True)
    ready = models.DateTimeField()
    start = models.DateTimeField(null=True, blank=True)
    end = models.DateTimeField(null=True, blank=True)
    result = models.CharField(max_length=250)



