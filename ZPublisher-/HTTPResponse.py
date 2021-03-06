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
'''CGI Response Output formatter

$Id: HTTPResponse.py,v 1.2 2001/03/03 18:44:41 henning Exp $'''
__version__='$Revision: 1.2 $'[11:-2]

import string, types, sys, regex, re
from string import find, rfind, lower, upper, strip, split, join, translate
from types import StringType, InstanceType, LongType
from BaseResponse import BaseResponse

nl2sp=string.maketrans('\n',' ')

status_reasons={
100: 'Continue',
101: 'Switching Protocols',
102: 'Processing',
200: 'OK',
201: 'Created',
202: 'Accepted',
203: 'Non-Authoritative Information',
204: 'No Content',
205: 'Reset Content',
206: 'Partial Content',
207: 'Multi-Status',
300: 'Multiple Choices',
301: 'Moved Permanently',
302: 'Moved Temporarily',
303: 'See Other',
304: 'Not Modified',
305: 'Use Proxy',
307: 'Temporary Redirect',
400: 'Bad Request',
401: 'Unauthorized',
402: 'Payment Required',
403: 'Forbidden',
404: 'Not Found',
405: 'Method Not Allowed',
406: 'Not Acceptable',
407: 'Proxy Authentication Required',
408: 'Request Time-out',
409: 'Conflict',
410: 'Gone',
411: 'Length Required',
412: 'Precondition Failed',
413: 'Request Entity Too Large',
414: 'Request-URI Too Large',
415: 'Unsupported Media Type',
416: 'Requested range not satisfiable',
417: 'Expectation Failed',
422: 'Unprocessable Entity',
423: 'Locked',
424: 'Failed Dependency',
500: 'Internal Server Error',
501: 'Not Implemented',
502: 'Bad Gateway',
503: 'Service Unavailable',
504: 'Gateway Time-out',
505: 'HTTP Version not supported',
507: 'Insufficient Storage',
}

status_codes={}
# Add mappings for builtin exceptions and
# provide text -> error code lookups.
for key, val in status_reasons.items():
    status_codes[lower(join(split(val, ' '), ''))]=key
    status_codes[lower(val)]=key
    status_codes[key]=key
    status_codes[str(key)]=key
en=filter(lambda n: n[-5:]=='Error', dir(__builtins__))
for name in map(lower, en):
    status_codes[name]=500
status_codes['nameerror']=503
status_codes['keyerror']=503
status_codes['redirect']=300


start_of_header_search=re.compile('(<head[^>]*>)', re.IGNORECASE).search

accumulate_header={'set-cookie': 1}.has_key

class HTTPResponse(BaseResponse):
    """\
    An object representation of an HTTP response.
    
    The Response type encapsulates all possible responses to HTTP
    requests.  Responses are normally created by the object publisher.
    A published object may recieve the response abject as an argument
    named 'RESPONSE'.  A published object may also create it's own
    response object.  Normally, published objects use response objects
    to:

    - Provide specific control over output headers,

    - Set cookies, or

    - Provide stream-oriented output.

    If stream oriented output is used, then the response object
    passed into the object must be used.
    """ #'

    accumulated_headers=''
    body=''
    realm='Zope'
    _error_format='text/html'
    _locked_status = 0

    def __init__(self,body='',status=200,headers=None,
                 stdout=sys.stdout, stderr=sys.stderr,):
        '''\
        Creates a new response. In effect, the constructor calls
        "self.setBody(body); self.setStatus(status); for name in
        headers.keys(): self.setHeader(name, headers[name])"
        '''
        if headers is None: headers={}
        self.headers=headers

        if status==200:
            self.status=200
            self.errmsg='OK'
            headers['status']="200 OK"      
        else: self.setStatus(status)
        self.base=''
        if body: self.setBody(body)
        self.cookies={}
        self.stdout=stdout
        self.stderr=stderr

    def retry(self):
        """Return a response object to be used in a retry attempt
        """
        
        # This implementation is a bit lame, because it assumes that
        # only stdout stderr were passed to the constructor. OTOH, I
        # think that that's all that is ever passed.
        
        return self.__class__(stdout=self.stdout, stderr=self.stderr)
    
    def setStatus(self, status, reason=None):
        '''\
        Sets the HTTP status code of the response; the argument may
        either be an integer or a string from { OK, Created, Accepted,
        NoContent, MovedPermanently, MovedTemporarily,
        NotModified, BadRequest, Unauthorized, Forbidden,
        NotFound, InternalError, NotImplemented, BadGateway,
        ServiceUnavailable } that will be converted to the correct
        integer value. '''
        if self._locked_status:
            # Don't change the response status.
            # It has already been determined.
            return
                
        if type(status) is types.StringType:
            status=lower(status)
        if status_codes.has_key(status): status=status_codes[status]
        else: status=500
        self.status=status
        if reason is None:
            if status_reasons.has_key(status): reason=status_reasons[status]
            else: reason='Unknown'
        self.setHeader('Status', "%d %s" % (status,str(reason)))
        self.errmsg=reason

    def setHeader(self, name, value, literal=0):
        '''\
        Sets an HTTP return header "name" with value "value", clearing
        the previous value set for the header, if one exists. If the
        literal flag is true, the case of the header name is preserved,
        otherwise word-capitalization will be performed on the header
        name on output.'''
        key=lower(name)
        if accumulate_header(key):
            self.accumulated_headers=(
                "%s%s: %s\n" % (self.accumulated_headers, name, value))
            return
        name=literal and name or key
        self.headers[name]=value

    def addHeader(self, name, value):
        '''\
        Set a new HTTP return header with the given value, while retaining
        any previously set headers with the same name.'''
        self.accumulated_headers=(
            "%s%s: %s\n" % (self.accumulated_headers, name, value))

    __setitem__=setHeader

    def setBody(self, body, title='', is_error=0,
                bogus_str_search=regex.compile(" [a-fA-F0-9]+>$").search,
                latin1_alias_match=re.compile(
                r'text/html(\s*;\s*charset=((latin)|(latin[-_]?1)|'
                r'(cp1252)|(cp819)|(csISOLatin1)|(IBM819)|(iso-ir-100)|'
                r'(iso[-_]8859[-_]1(:1987)?)))?$',re.I).match
                ):
        '''\
        Set the body of the response
        
        Sets the return body equal to the (string) argument "body". Also
        updates the "content-length" return header.

        You can also specify a title, in which case the title and body
        will be wrapped up in html, head, title, and body tags.

        If the body is a 2-element tuple, then it will be treated
        as (title,body)
        
        If is_error is true then the HTML will be formatted as a Zope error
        message instead of a generic HTML page.
        '''
        if not body: return self
        
        if type(body) is types.TupleType and len(body) == 2:
            title,body=body

        if type(body) is not types.StringType:
            if hasattr(body,'asHTML'):
                body=body.asHTML()

        body=str(body)
        l=len(body)
        if ((l < 200) and body[:1]=='<' and find(body,'>')==l-1 and 
            bogus_str_search(body) > 0):
            self.notFoundError(body[1:-1])
        else:
            if(title):
                title=str(title)
                if not is_error:
                    self.body=self._html(title, body)
                else:
                    self.body=self._error_html(title, body)
            else:
                self.body=body


        if not self.headers.has_key('content-type'):
            isHTML=self.isHTML(body)
            if isHTML: c='text/html'
            else:      c='text/plain'
            self.setHeader('content-type', c)

        # Some browsers interpret certain characters in Latin 1 as html
        # special characters. These cannot be removed by html_quote,
        # because this is not the case for all encodings.
        content_type=self.headers['content-type']
        if content_type == 'text/html' or latin1_alias_match(
            content_type) is not None:
            body = join(split(body,'\213'),'&lt;')
            body = join(split(body,'\233'),'&gt;')

        self.setHeader('content-length', len(self.body))
        self.insertBase()
        return self

    def setBase(self,base):
        'Set the base URL for the returned document.'
        if base[-1:] != '/':
            base=base+'/'
        self.base=base

    def insertBase(self,
                   base_re_search=regex.compile('\(<base[\0- ]+[^>]+>\)',
                                                regex.casefold).search
                   ):

        # Only insert a base tag if content appears to be html.
        content_type = split(self.headers.get('content-type', ''), ';')[0]
        if content_type and (content_type != 'text/html'):
            return

        if self.base:
            body=self.body
            if body:
                match=start_of_header_search(body)
                if match is not None:
                    index=match.start(0) + len(match.group(0))
                    ibase=base_re_search(body)
                    if ibase < 0:
                        self.body=('%s\n<base href="%s" />\n%s' %
                                   (body[:index], self.base, body[index:]))
                        self.setHeader('content-length', len(self.body))

    def appendCookie(self, name, value):
        '''\
        Returns an HTTP header that sets a cookie on cookie-enabled
        browsers with a key "name" and value "value". If a value for the
        cookie has previously been set in the response object, the new
        value is appended to the old one separated by a colon. '''

        cookies=self.cookies
        if cookies.has_key(name): cookie=cookies[name]
        else: cookie=cookies[name]={}
        if cookie.has_key('value'):
            cookie['value']='%s:%s' % (cookie['value'], value)
        else: cookie['value']=value

    def expireCookie(self, name, **kw):
        '''\
        Cause an HTTP cookie to be removed from the browser
        
        The response will include an HTTP header that will remove the cookie
        corresponding to "name" on the client, if one exists. This is
        accomplished by sending a new cookie with an expiration date
        that has already passed. Note that some clients require a path
        to be specified - this path must exactly match the path given
        when creating the cookie. The path can be specified as a keyword
        argument.
        '''
        dict={'max_age':0, 'expires':'Wed, 31-Dec-97 23:59:59 GMT'}
        for k, v in kw.items():
            dict[k]=v
        apply(HTTPResponse.setCookie, (self, name, 'deleted'), dict)

    def setCookie(self,name,value,**kw):
        '''\
        Set an HTTP cookie on the browser

        The response will include an HTTP header that sets a cookie on
        cookie-enabled browsers with a key "name" and value
        "value". This overwrites any previously set value for the
        cookie in the Response object.
        '''
        cookies=self.cookies
        if cookies.has_key(name):
            cookie=cookies[name]
        else: cookie=cookies[name]={}
        for k, v in kw.items():
            cookie[k]=v
        cookie['value']=value

    def appendHeader(self, name, value, delimiter=","):
        '''\
        Append a value to a cookie
        
        Sets an HTTP return header "name" with value "value",
        appending it following a comma if there was a previous value
        set for the header. '''
        headers=self.headers
        if headers.has_key(name):
            h=self.header[name]
            h="%s%s\n\t%s" % (h,delimiter,value)
        else: h=value
        self.setHeader(name,h)

    def isHTML(self,str):
        return lower(strip(str)[:6]) == '<html>' or find(str,'</') > 0

    def quoteHTML(self,text,
                  subs={'&':'&amp;', "<":'&lt;', ">":'&gt;', '\"':'&quot;'}
                  ):
        for ent in '&<>\"':
            if find(text, ent) >= 0:
                text=join(split(text,ent),subs[ent])

        return text
         

    def format_exception(self,etype,value,tb,limit=None):
        import traceback
        result=['Traceback (innermost last):']
        if limit is None:
                if hasattr(sys, 'tracebacklimit'):
                        limit = sys.tracebacklimit
        n = 0
        while tb is not None and (limit is None or n < limit):
                f = tb.tb_frame
                lineno = tb.tb_lineno
                co = f.f_code
                filename = co.co_filename
                name = co.co_name
                locals=f.f_locals
                result.append('  File %s, line %d, in %s'
                              % (filename,lineno,name))
                try: result.append('    (Object: %s)' %
                                   locals[co.co_varnames[0]].__name__)
                except: pass
                try: result.append('    (Info: %s)' %
                                   str(locals['__traceback_info__']))
                except: pass
                tb = tb.tb_next
                n = n+1
        result.append(join(traceback.format_exception_only(etype, value),
                           ' '))
        return result

    def _traceback(self,t,v,tb):
        tb=self.format_exception(t,v,tb,200)
        tb=join(tb,'\n')
        tb=self.quoteHTML(tb)
        if self.debug_mode: _tbopen, _tbclose = '<PRE>', '</PRE>'
        else:               _tbopen, _tbclose = '<!--',  '-->'
        return "\n%s\n%s\n%s" % (_tbopen, tb, _tbclose)

    def redirect(self, location, status=302, lock=0):
        """Cause a redirection without raising an error"""
        self.setStatus(status)
        self.setHeader('Location', location)

        if lock:
            # Don't let anything change the status code.
            # The "lock" argument needs to be set when redirecting
            # from a standard_error_message page.
            self._locked_status = 1
        return location


    def _html(self,title,body):
        return ("<html>\n"
                "<head>\n<title>%s</title>\n</head>\n"
                "<body>\n%s\n</body>\n"
                "</html>\n" % (title,body))

    def _error_html(self,title,body):
        # XXX could this try to use standard_error_message somehow?
        return ("""\
<HTML>
<HEAD><TITLE>Zope Error</TITLE></HEAD>
<BODY>

<TABLE BORDER="0" WIDTH="100%">
<TR VALIGN="TOP">

<TD WIDTH="10%" ALIGN="CENTER">
&nbsp;
</TD>

<TD WIDTH="90%">
  <H2>Zope Error</H2>
  <P>Zope has encountered an error while publishing this resource.
  </P>""" + \
  """
  <P><STRONG>%s</STRONG></P>
  
  %s""" %(title,body) + \
  """
  <HR NOSHADE>

  <P>Troubleshooting Suggestions</P>

  <UL>
  <LI>The URL may be incorrect.</LI>
  <LI>The parameters passed to this resource may be incorrect.</LI>
  <LI>A resource that this resource relies on may be encountering an error.</LI>
  </UL>

  <P>For more detailed information about the error, please
  refer to the HTML source for this page.
  </P>

  <P>If the error persists please contact the site maintainer.
  Thank you for your patience.
  </P>
</TD></TR>
</TABLE>

</BODY>
</HTML>""")

    def notFoundError(self,entry='who knows!'):
        self.setStatus(404)
        raise 'NotFound',self._error_html(
            "Resource not found",
            "Sorry, the requested Zope resource does not exist.<p>" +
            "Check the URL and try again.<p>" +
            "\n<!--\n%s\n-->" % entry)

    forbiddenError=notFoundError  # If a resource is forbidden,
                                  # why reveal that it exists?

    def debugError(self,entry):
        raise 'NotFound',self._error_html(
            "Debugging Notice",
            "Zope has encountered a problem publishing your object.<p>"
            "\n%s" % entry)

    def badRequestError(self,name):
        self.setStatus(400)
        if regex.match('^[A-Z_0-9]+$',name) >= 0:
            raise 'InternalError', self._error_html(
                "Internal Error",
                "Sorry, an internal error occurred in this Zope resource.")

        raise 'BadRequest',self._error_html(
            "Invalid request",
            "The parameter, <em>%s</em>, " % name +
            "was omitted from the request.<p>" + 
            "Make sure to specify all required parameters, " +
            "and try the request again."
            )

    def _unauthorized(self):
        realm=self.realm
        if realm:
            self.setHeader('WWW-Authenticate', 'basic realm="%s"' % realm, 1)

    def unauthorized(self):
        self._unauthorized()
        m="<strong>You are not authorized to access this resource.</strong>"
        if self.debug_mode:
            if self._auth:
                m=m+'<p>\nUsername and password are not correct.'
            else:
                m=m+'<p>\nNo Authorization header found.'
        raise 'Unauthorized', m

    def exception(self, fatal=0, info=None,
                  absuri_match=regex.compile(
                      "^"
                      "\(/\|\([a-zA-Z0-9+.-]+:\)\)"
                      "[^\000- \"\\#<>]*"
                      "\\(#[^\000- \"\\#<>]*\\)?"
                      "$"
                      ).match,
                  tag_search=re.compile('[a-zA-Z]>').search,
                  abort=1
                  ):
        if type(info) is type(()) and len(info)==3: t,v,tb = info
        else: t,v,tb = sys.exc_info()

        if str(t)=='Unauthorized': self._unauthorized()

        stb=tb

        try:
            # Try to capture exception info for bci calls
            et=translate(str(t),nl2sp)
            self.setHeader('bobo-exception-type',et)
            ev=translate(str(v),nl2sp)
            if find(ev,'<html>') >= 0: ev='bobo exception'
            self.setHeader('bobo-exception-value',ev[:255])
            # Get the tb tail, which is the interesting part:
            while tb.tb_next is not None: tb=tb.tb_next
            el=str(tb.tb_lineno)
            ef=str(tb.tb_frame.f_code.co_filename)
            self.setHeader('bobo-exception-file',ef)
            self.setHeader('bobo-exception-line',el)

        except:
            # Dont try so hard that we cause other problems ;)
            pass

        tb=stb
        stb=None
        self.setStatus(t)
        if self.status >= 300 and self.status < 400:
            if type(v) == types.StringType and absuri_match(v) >= 0:
                if self.status==300: self.setStatus(302)
                self.setHeader('location', v)
                tb=None
                return self
            else:
                try:
                    l,b=v
                    if type(l) == types.StringType and absuri_match(l) >= 0:
                        if self.status==300: self.setStatus(302)
                        self.setHeader('location', l)
                        self.setBody(b)
                        tb=None
                        return self
                except: pass

        b=v
        if isinstance(b,Exception):
            try:
                b=str(b)
            except:
                b='<unprintable %s object>' % type(b).__name__
        
        if fatal and t is SystemExit and v.code==0:
                tb=self.setBody(
                    (str(t),
                    'Zope has exited normally.<p>'
                     + self._traceback(t,v,tb)),
                     is_error=1)
        #elif 1: self.setBody(v)

        elif type(b) is not types.StringType or tag_search(b) is None:
            tb=self.setBody(
                (str(t),
                'Sorry, a Zope error occurred.<p>'+
                 self._traceback(t,v,tb)),
                 is_error=1)

        elif lower(strip(b)[:6])=='<html>' or lower(strip(b)[:14])=='<!doctype html':
            # error is an HTML document, not just a snippet of html
            tb=self.setBody(b + self._traceback(t,'(see above)',tb),
                is_error=1)
        else:
            tb=self.setBody(
                (str(t), b + self._traceback(t,'(see above)',tb)),
                 is_error=1)

        return tb

    _wrote=None

    def _cookie_list(self):
        cookie_list=[]
        for name, attrs in self.cookies.items():

            # Note that as of May 98, IE4 ignores cookies with
            # quoted cookie attr values, so only the value part
            # of name=value pairs may be quoted.

            cookie='Set-Cookie: %s="%s"' % (name, attrs['value'])
            for name, v in attrs.items():
                name=lower(name)
                if name=='expires': cookie = '%s; Expires=%s' % (cookie,v)
                elif name=='domain': cookie = '%s; Domain=%s' % (cookie,v)
                elif name=='path': cookie = '%s; Path=%s' % (cookie,v)
                elif name=='max_age': cookie = '%s; Max-Age=%s' % (cookie,v)
                elif name=='comment': cookie = '%s; Comment=%s' % (cookie,v)
                elif name=='secure' and v: cookie = '%s; Secure' % cookie
            cookie_list.append(cookie)

        # Should really check size of cookies here!
        
        return cookie_list

    def __str__(self,
                html_search=regex.compile('<html>',regex.casefold).search,
                ):
        if self._wrote: return ''       # Streaming output was used.

        headers=self.headers
        body=self.body

        if not headers.has_key('content-length') and \
                not headers.has_key('transfer-encoding'):
            self.setHeader('content-length',len(body))

        # ugh - str(content-length) could be a Python long, which will
        # produce a trailing 'L' :( This can go away when we move to
        # Python 2.0...
        content_length= headers.get('content-length', None)
        if type(content_length) is LongType:
            str_rep=str(content_length)
            if str_rep[-1:]=='L':
                str_rep=str_rep[:-1]
                self.setHeader('content-length', str_rep)

        headersl=[]
        append=headersl.append

        # status header must come first.
        append("Status: %s" % headers.get('status', '200 OK'))
        append("X-Powered-By: Zope (www.zope.org), Python (www.python.org)")
        if headers.has_key('status'):
            del headers['status']
        for key, val in headers.items():
            if lower(key)==key:
                # only change non-literal header names
                key="%s%s" % (upper(key[:1]), key[1:])
                start=0
                l=find(key,'-',start)
                while l >= start:
                    key="%s-%s%s" % (key[:l],upper(key[l+1:l+2]),key[l+2:])
                    start=l+1
                    l=find(key,'-',start)
            append("%s: %s" % (key, val))
        if self.cookies:
            headersl=headersl+self._cookie_list()
        headersl[len(headersl):]=[self.accumulated_headers, body]
        return join(headersl,'\n')

    def write(self,data):
        """\
        Return data as a stream

        HTML data may be returned using a stream-oriented interface.
        This allows the browser to display partial results while
        computation of a response to proceed.

        The published object should first set any output headers or
        cookies on the response object.

        Note that published objects must not generate any errors
        after beginning stream-oriented output. 

        """
        if not self._wrote:
            self.outputBody()
            self._wrote=1
            self.stdout.flush()

        self.stdout.write(data)
