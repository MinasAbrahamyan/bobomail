##############################################################################
# 
# Zope Public License (ZPL) Version 1.0
# -------------------------------------
# 
# Copyright (c) Digital Creations.  All rights reserved.
# 
# This license has been certified as Open Source(tm).
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
# 1. Redistributions in source code must retain the above copyright
#    notice, this list of conditions, and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions, and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
# 
# 3. Digital Creations requests that attribution be given to Zope
#    in any manner possible. Zope includes a "Powered by Zope"
#    button that is installed by default. While it is not a license
#    violation to remove this button, it is requested that the
#    attribution remain. A significant investment has been put
#    into Zope, and this effort will continue if the Zope community
#    continues to grow. This is one way to assure that growth.
# 
# 4. All advertising materials and documentation mentioning
#    features derived from or use of this software must display
#    the following acknowledgement:
# 
#      "This product includes software developed by Digital Creations
#      for use in the Z Object Publishing Environment
#      (http://www.zope.org/)."
# 
#    In the event that the product being advertised includes an
#    intact Zope distribution (with copyright and license included)
#    then this clause is waived.
# 
# 5. Names associated with Zope or Digital Creations must not be used to
#    endorse or promote products derived from this software without
#    prior written permission from Digital Creations.
# 
# 6. Modified redistributions of any form whatsoever must retain
#    the following acknowledgment:
# 
#      "This product includes software developed by Digital Creations
#      for use in the Z Object Publishing Environment
#      (http://www.zope.org/)."
# 
#    Intact (re-)distributions of any official Zope release do not
#    require an external acknowledgement.
# 
# 7. Modifications are encouraged but must be packaged separately as
#    patches to official Zope releases.  Distributions that do not
#    clearly separate the patches from the original work must be clearly
#    labeled as unofficial distributions.  Modifications which do not
#    carry the name Zope may be packaged in any form, as long as they
#    conform to all of the clauses above.
# 
# 
# Disclaimer
# 
#   THIS SOFTWARE IS PROVIDED BY DIGITAL CREATIONS ``AS IS'' AND ANY
#   EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#   IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
#   PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL DIGITAL CREATIONS OR ITS
#   CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#   SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#   LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
#   USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#   ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
#   OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
#   OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
#   SUCH DAMAGE.
# 
# 
# This software consists of contributions made by Digital Creations and
# many individuals on behalf of Digital Creations.  Specific
# attributions are listed in the accompanying credits file.
# 
##############################################################################
__doc__="""Python Object Publisher -- Publish Python objects on web servers

$Id: Publish.py,v 1.2 2001/03/03 18:44:41 henning Exp $"""
__version__='$Revision: 1.2 $'[11:-2]

import sys, os
from string import lower, atoi, rfind, strip
from Response import Response
from Request import Request
from maybe_lock import allocate_lock
from mapply import mapply

class Retry(Exception):
    """Raise this to retry a request
    """

    def __init__(self, t=None, v=None, tb=None):
        self._args=t, v, tb

    def reraise(self):
        t, v, tb = self._args
        if t is None: t=Retry
        if tb is None: raise t, v
        try: raise t, v, tb
        finally: tb=None

def call_object(object, args, request):
    result=apply(object,args) # Type s<cr> to step into published object.
    return result

def missing_name(name, request):
    if name=='self': return request['PARENTS'][0]
    request.response.badRequestError(name)

def dont_publish_class(klass, request):
    request.response.forbiddenError("class %s" % klass.__name__)

def publish(request, module_name, after_list, debug=0,
            # Optimize:
            call_object=call_object,
            missing_name=missing_name,
            dont_publish_class=dont_publish_class,
            mapply=mapply,
            ):

    (bobo_before, bobo_after, object, realm, debug_mode, err_hook,
     validated_hook, transactions_manager)= get_module_info(module_name)

    parents=None

    try:
        request.processInputs()

        request_get=request.get
        response=request.response
    
        # First check for "cancel" redirect:
        cancel=''
        if lower(strip(request_get('SUBMIT','')))=='cancel':
            cancel=request_get('CANCEL_ACTION','')
            if cancel: raise 'Redirect', cancel
    
        after_list[0]=bobo_after
        if debug_mode: response.debug_mode=debug_mode
        if realm and not request.get('REMOTE_USER',None):
            response.realm=realm
    
        if bobo_before is not None:
            bobo_before()
    
        # Get a nice clean path list:
        path=strip(request_get('PATH_INFO'))
    
        request['PARENTS']=parents=[object]
        
        if transactions_manager: transactions_manager.begin()
    
        object=request.traverse(path, validated_hook=validated_hook)
    
        if transactions_manager:
            transactions_manager.recordMetaData(object, request)
    
        result=mapply(object, request.args, request,
                      call_object,1,
                      missing_name, 
                      dont_publish_class,
                      request, bind=1)
    
        if result is not response: response.setBody(result)
    
        if transactions_manager: transactions_manager.commit()

        return response
    except:
        if transactions_manager: transactions_manager.abort()
        
        if err_hook is not None:
            if parents: parents=parents[0]
            try:
                return err_hook(parents, request,
                                sys.exc_info()[0],
                                sys.exc_info()[1],
                                sys.exc_info()[2],
                                )
            except Retry:
                # We need to try again....
                if not request.supports_retry():
                    return err_hook(parents, request,
                                    sys.exc_info()[0],
                                    sys.exc_info()[1],
                                    sys.exc_info()[2],
                                    )
                newrequest=request.retry()
                try:
                    return publish(newrequest, module_name, after_list, debug)
                finally:
                    newrequest.close()
                    
        else: raise
            

def publish_module(module_name,
                   stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr,
                   environ=os.environ, debug=0, request=None, response=None):
    must_die=0
    status=200
    after_list=[None]
    try:
        try:
            if response is None:
                response=Response(stdout=stdout, stderr=stderr)
            else:
                stdout=response.stdout

            if request is None:
                request=Request(stdin, environ, response)

            response = publish(request, module_name, after_list, debug=debug)
        except SystemExit, v:
            must_die=sys.exc_info()
            request.response.exception(must_die)
        except ImportError, v:
            if type(v) is type(()) and len(v)==3: must_die=v
            elif hasattr(sys, 'exc_info'): must_die=sys.exc_info()
            else: must_die = SystemExit, v, sys.exc_info()[2]
            request.response.exception(1, v)
        except:
            request.response.exception()
            status=response.getStatus()

        if response:
            outputBody=getattr(response, 'outputBody', None)
            if outputBody is not None:
                outputBody()
            else:
                response=str(response)
                if response: stdout.write(response)

        # The module defined a post-access function, call it
        if after_list[0] is not None: after_list[0]()

    finally:
        if request is not None: request.close()

    if must_die:
        try: raise must_die[0], must_die[1], must_die[2]
        finally: must_die=None

    return status


_l=allocate_lock()
def get_module_info(module_name, modules={},
                    acquire=_l.acquire,
                    release=_l.release,
                    ):

    if modules.has_key(module_name): return modules[module_name]

    if module_name[-4:]=='.cgi': module_name=module_name[:-4]

    acquire()
    tb=None
    try:
        try:
            module=__import__(module_name, globals(), globals(), ('__doc__',))

            realm=module_name

            # Let the app specify a realm
            if hasattr(module,'__bobo_realm__'):
                realm=module.__bobo_realm__
            elif os.environ.has_key('Z_REALM'):
                realm=os.environ['Z_REALM']
            elif os.environ.has_key('BOBO_REALM'):
                realm=os.environ['BOBO_REALM']
            else: realm=module_name

            # Check for debug mode
            if hasattr(module,'__bobo_debug_mode__'):
                debug_mode=not not module.__bobo_debug_mode__
            elif (os.environ.has_key('Z_DEBUG_MODE') or
                  os.environ.has_key('BOBO_DEBUG_MODE')):
                if os.environ.has_key('Z_DEBUG_MODE'):
                    debug_mode=lower(os.environ['Z_DEBUG_MODE'])
                else:
                    debug_mode=lower(os.environ['BOBO_DEBUG_MODE'])
                if debug_mode=='y' or debug_mode=='yes':
                    debug_mode=1
                else:
                    try: debug_mode=atoi(debug_mode)
                    except: debug_mode=None
            else: debug_mode=None

            if hasattr(module,'__bobo_before__'):
                bobo_before=module.__bobo_before__
            else: bobo_before=None

            if hasattr(module,'__bobo_after__'): bobo_after=module.__bobo_after__
            else: bobo_after=None

            if hasattr(module,'bobo_application'):
                object=module.bobo_application
            elif hasattr(module,'web_objects'):
                object=module.web_objects
            else: object=module

            error_hook=getattr(module,'zpublisher_exception_hook', None)
            validated_hook=getattr(module,'zpublisher_validated_hook', None)

            transactions_manager=getattr(
                module,'zpublisher_transactions_manager', None)
            if not transactions_manager:
                try: get_transaction()
                except: pass
                else:
                    # Create a default transactions manager for use
                    # by software that uses ZPublisher and ZODB but
                    # not the rest of Zope.
                    transactions_manager = DefaultTransactionsManager()

            info= (bobo_before, bobo_after, object, realm, debug_mode,
                   error_hook, validated_hook, transactions_manager)

            modules[module_name]=modules[module_name+'.cgi']=info
            
            return info
        except:
            t,v,tb=sys.exc_info()
            v=str(v)
            raise ImportError, (t, v), tb
    finally:
        tb=None
        release()


class DefaultTransactionsManager:
    def begin(self): get_transaction().begin()
    def commit(self): get_transaction().commit()
    def abort(self): get_transaction().abort()
    def recordMetaData(self, object, request):
        # Is this code needed?
        request_get = request.get
        T=get_transaction()
        T.note(request_get('PATH_INFO'))
        auth_user=request_get('AUTHENTICATED_USER',None)
        if auth_user is not None:
            T.setUser(auth_user, request_get('AUTHENTICATION_PATH'))
        

# ZPublisher profiler support
# ---------------------------

if os.environ.get('PROFILE_PUBLISHER', None):

    import profile, pstats

    _pfile=os.environ['PROFILE_PUBLISHER']
    _plock=allocate_lock()
    _pfunc=publish_module
    _pstat=None

    def pm(module_name, stdin, stdout, stderr, 
           environ, debug, request, response):
        try:
            r=_pfunc(module_name, stdin=stdin, stdout=stdout, 
                     stderr=stderr, environ=environ, debug=debug, 
                     request=request, response=response)
        except: r=None
        sys._pr_=r

    def publish_module(module_name, stdin=sys.stdin, stdout=sys.stdout, 
                       stderr=sys.stderr, environ=os.environ, debug=0, 
                       request=None, response=None):
        _plock.acquire()
        try:
            if request is not None:
                path_info=request.get('PATH_INFO')
            else: path_info=environ.get('PATH_INFO')
            if path_info[-14:]=='manage_profile':
                return _pfunc(module_name, stdin=stdin, stdout=stdout, 
                              stderr=stderr, environ=environ, debug=debug, 
                              request=request, response=response)
            pobj=profile.Profile()
            pobj.runcall(pm, module_name, stdin, stdout, stderr, 
                         environ, debug, request, response)
            result=sys._pr_
            pobj.create_stats()
            if _pstat is None:
                global _pstat
                _pstat=sys._ps_=pstats.Stats(pobj)
            else: _pstat.add(pobj)
        finally:
            _plock.release()

        if result is None:
            try:
                error=sys.exc_info()
                file=open(_pfile, 'w')
                sys.stdout=file
                _pstat.strip_dirs().sort_stats('cumulative').print_stats(250)
                _pstat.strip_dirs().sort_stats('time').print_stats(250)
                file.flush()
                file.close()
            except: pass
            raise error[0], error[1], error[2]
        return result



