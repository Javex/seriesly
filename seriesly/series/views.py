import logging

from google.appengine.api import users

from django.http import HttpResponse,HttpResponseRedirect,Http404
from django.core.urlresolvers import reverse
from django.conf import settings

from helper import is_get, is_post
from series.models import Show, Episode
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from series.tvrage import TVRage


def import_shows(request):
    from series_list import series_list
    show_names = series_list.split("\n")
    Show.clear_cache()
    for show_name in show_names:
        Show.update_or_create(show_name)
    Show.clear_cache()
    return HttpResponse("Done")
    
def import_show(request):
    this_url = reverse("seriesly-shows-import_show")
    user = users.get_current_user()
    nick = "Anonymous"
    if user:
        nick = user.nickname()
    if not user or user.email() not in settings.ADMIN_USERS:
        return HttpResponse("""Hi %s,<a href=\"%s\">Sign in</a>.""" % (nick, users.create_login_url(this_url)))
        #return HttpResponse("""Hi %s,<br/>
        #    <a href="http://services.tvrage.com/feeds/search.php?show=">Search for shows on TVRage</a><br/>
        #    Enter TV Rage ID: <form action="." method="post">
        #    <input type="text" name="show"/><input type="submit"/></form><a href="%s">Logout</a>""" % (nick, users.create_logout_url(this_url)))
    name = request.POST.get("show", None)
    if name:
        if name.startswith("!"):
            Show.update_or_create(name[1:])
        else:
            show_id = int(name)
            Show.update_or_create(None, show_id)
        Show.clear_cache()
        Episode.clear_cache()
        return HttpResponseRedirect(this_url+"?status=Done")
    
    show = None
    if request.POST.get("search_name", None):
        show = search_show(request)
        
        
    return render_to_response("import_show.html", RequestContext(request, 
                 {'name' : nick, 'logout_url' : users.create_logout_url(this_url), 'show' : show, 'search_name' : request.POST.get("search_name", None)}))
        

def update(request):
    shows = Show.get_all_ordered()
    for show in shows:
        show.add_update_task()
    Episode.add_clear_cache_task("series")
    return HttpResponse("Done: %d" % (len(shows)))

@is_post
def update_show(request):
    key = None
    show = None
    try:
        key = request.POST.get("key", None)
        if key is None:
            raise Http404
        show = Show.get_all_dict().get(key, None)
        if show is None:
            raise Http404
        show.update()
    except Http404:
        raise Http404
    except Exception, e:
        logging.error("Error Updating Show (%s)%s: %s" % (show, key, e))
        return HttpResponse("Done (with errors, %s(%s))" % (show,key))
    logging.debug("Done updating show %s(%s)" % (show,key))
    return HttpResponse("Done: %s(%s)" % (show,key))
    
def redirect_to_front(request, episode_id):
    return HttpResponseRedirect("/")
    
def clear_cache(request):
    Show.clear_cache()
    Episode.clear_cache()
    return HttpResponse("Done.")

@is_get
def redirect_to_amazon(request, show_id):
    show = Show.get_by_id(int(show_id))
    if show is None:
        raise Http404
    if not show.amazon_url:
        raise Http404
    return HttpResponseRedirect(show.amazon_url)

@is_post
def search_show(request):
    show_name = request.POST.get('search_name', "")
    if not show_name:
        return None
    
    tvrage = TVRage()
    show = tvrage.get_info_by_name(show_name)
    if not show:
        return None
    return show
    