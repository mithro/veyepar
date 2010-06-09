#!/usr/bin/python

# posts to blip.tv

import blip_uploader

import re
import os
import xml.etree.ElementTree

import pw
from process import process

from main.models import Show, Location, Episode, Raw_File, Cut_List

# this is here so ckblip can import roles
# http://wiki.blip.tv/index.php/Roles
    # old, works.. but Source looks better:    'ogv':"Web", 
roles={
        'ogv':"Master", 
        'flv':"Web", 
        'mp4':"dvd", 
        'm4v':"Portable (iPod)", 
        'ogg':"Portable (other)", 
        'mp3':"Audio-only", 
    }

class post(process):

  ready_state = 4

  def process_ep(self, ep):
    print ep.id, ep.name
    loc = ep.location
    show = ep.show
    client = show.client

    descriptions = [ep.description, show.description, client.description]
    descriptions = [d for d in descriptions if d]
    description = "%s</br>\n".join(descriptions)

    blip_cli=blip_uploader.Blip_CLI()
    blip_cli.debug = self.options.verbose

    meta = {
        'title': ep.name,
        'description': description,
        }

# if .target is blank, a new episode will be created and .target set
# else it will use the id of the episode from a previous run. 
    video_id = ep.target

    tags = [ self.options.topics, client.slug, client.tags, ep.tags ]
    meta['topics'] = ' '.join([tag for tag in tags if tag] )

    if ep.license: 
        meta['license'] = str(ep.license)
    elif self.options.license:
        meta['license'] = self.options.license

    if self.options.rating:
        meta['content_rating'] = self.options.rating

    if self.options.category:
        meta['categories_id'] = self.options.category

    if self.options.hidden:
        meta['hidden'] = self.options.hidden

    # find a thumbnail
    # check for episode.tumb used in the following:
    # 1. absololute path (dumb?)
    # 2. in tumb dir (smart)
    # 3. relitive to show dir (not completely wonky)
    # 4. in tumb dir, same name as episode.png (smart)
    # if none of those, then grab the thumb from the first cut list file
    found=False
    for thumb in [ 
          ep.thumbnail,
          os.path.join(self.show_dir,'thumb',ep.thumbnail),
          os.path.join(self.show_dir,ep.thumbnail),
          os.path.join(self.show_dir,'thumb',ep.slug+".png"),]:
          if os.path.isfile(thumb): 
              found=True
              break
    if not found:
         for cut in Cut_List.objects.filter(
                 episode=ep,apply=True).order_by('sequence'):
             basename = cut.raw_file.basename()        
             thumb=os.path.join(self.episode_dir, "%s.png"%(basename))
             if os.path.exists(thumb): 
                 found=True
                 break
    if not found: thumb=''

    
# the blip api gets kinda funky around multiple uploads
# so no surprise the code is kinda funky.
    files = []
    exts = self.options.upload_formats.split()
# pull dv from the list
    exts = [e for e in exts if e != 'dv']
    for i,ext in enumerate(exts):
        fileno=str(i) if i else ''
        role=roles.get(ext,'extra')
        src_pathname = os.path.join( self.show_dir, ext, "%s.%s"%(ep.slug,ext))
        files.append((fileno,role,src_pathname))

    # use the username for the client, else use the first user in pw.py
    blip_user =  client.blip_user if client.blip_user \
                    else pw.blip.keys()[0]
    blip_pw = pw.blip[blip_user]

    if self.options.test:
        print 'test mode:'
        print 'blip_cli.Upload( video_id, user, pw, files, meta, thumb)'
        print video_id
        print 'files %s' % files
        print 'meta %s' % meta
        print 'thumb %s' % thumb
        print
    
        blipcmd = "./blip_uploader.py --fileno %s --role %s --filename %s" % (files[0])
        blipcmd += " --thumb %s" % thumb 
        for i in meta.items():
            blipcmd += " --%s %s" % i 
        print blipcmd 

    else:
        
        response = blip_cli.Upload(
            video_id, blip_user, blip_pw, files, meta, thumb)
        response_xml = response.read()
        if self.options.verbose: print response_xml

        """
<otterResponses>
<response>
Your file called Test Episode #0 has been successfully posted.
<post_url>http://blip.tv/file/3734423</post_url>
</response>

</otterResponses>
"""
# (02:37:51 PM) Juhaz: CarlFK, no. tree is the root element, it can't find itself, only children.
        tree = xml.etree.ElementTree.fromstring(response_xml)

        # self.log_info(response_xml)
        ep.comment += "\n%s\n" % response_xml
        blip_urls=tree.findall('response/post_url')
        # blip_urls = re.search("post_url>(.*)</post" ,response_xml).groups()

        if blip_urls:
            blip_url=blip_urls[0].text
            blip_id=blip_url[-7:]
            if self.options.verbose:
                print blip_url, blip_id
            ep.target = blip_id
            ep.comment += blip_url
            self.log_info(blip_url)
            ret=True
        else:
            # don't print it again if it was just printed 
            if not self.options.verbose: print response_xml
            ep.comment += "upload failed\n%s\n" % response_xml
            ret=False
        ep.save()

        return ret

  def add_more_options(self, parser):
        parser.add_option('--rating', 
            help="TV rating")
        parser.add_option('-T', '--topics',
            help="list of topics (user defined)")
        parser.add_option('-L', '--license',
            help="13 is Creative Commons Attribution-NC-ShareAlike 3.0\n"
            "'./blip_uploader.py -L list' to see full list" )
        parser.add_option('-C', '--category',
            help = "'./blip_uploader.py -C list' to see full list" )
        parser.add_option('--hidden',
            help="availability on blip.tv, 0=Available, 1=Hidden, 2=Available to family, 4=Available to friends/family.")


if __name__ == '__main__':
    p=post()
    p.main()

