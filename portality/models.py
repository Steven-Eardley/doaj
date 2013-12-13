from datetime import datetime
from copy import deepcopy
import json

from portality.core import app
from portality.dao import DomainObject as DomainObject

from werkzeug import generate_password_hash, check_password_hash
from flask.ext.login import UserMixin

############################################################################
# Generic/Utility classes and functions
############################################################################

class GenericBibJSON(object):
    # vocab of known identifier types
    P_ISSN = "pissn"
    E_ISSN = "eissn"
    DOI = "doi"
    
    # constructor
    def __init__(self, bibjson=None):
        self.bibjson = bibjson if bibjson is not None else {}
    
    # generic property getter and setter for ad-hoc extensions
    def get_property(self, prop):
        return self.bibjson.get(prop)
    
    def set_property(self, prop, value):
        self.bibjson[prop] = value
    
    # shared simple property getter and setters
        
    @property
    def title(self): return self.bibjson.get("title")
    @title.setter
    def title(self, val) : self.bibjson["title"] = val
    
    # complex getters and setters
    
    def _normalise_identifier(self, idtype, value):
        if idtype in [self.P_ISSN, self.E_ISSN]:
            return self._normalise_issn(value)
        return value
    
    def _normalise_issn(self, issn):
        issn = issn.upper()
        if len(issn) > 8: return issn
        if len(issn) == 8:
            if "-" in issn: return "0" + issn
            else: return issn[:4] + "-" + issn[4:]
        if len(issn) < 8:
            if "-" in issn: return ("0" * (9 - len(issn))) + issn
            else:
                issn = ("0" * (8 - len(issn))) + issn
                return issn[:4] + "-" + issn[4:]
    
    def add_identifier(self, idtype, value):
        if "identifier" not in self.bibjson:
            self.bibjson["identifier"] = []
        idobj = {"type" : idtype, "id" : self._normalise_identifier(idtype, value)}
        self.bibjson["identifier"].append(idobj)
    
    def get_identifiers(self, idtype=None):
        if idtype is None:
            return self.bibjson.get("identifier", [])
        
        ids = []
        for identifier in self.bibjson.get("identifier", []):
            if identifier.get("type") == idtype and identifier.get("id") not in ids:
                ids.append(identifier.get("id"))
        return ids
    
    def remove_identifiers(self, idtype=None, id=None):
        # if we are to remove all identifiers, this is easy
        if idtype is None and id is None:
            self.bibjson["identifier"] = []
            return
        
        # else, find all the identifiers positions that we need to remove
        idx = 0
        remove = []
        for identifier in self.bibjson.get("identifier", []):
            if idtype is not None and id is None:
                if identifier.get("type") == idtype:
                    remove.append(idx)
            elif idtype is None and id is not None:
                if identifier.get("id") == id:
                    remove.append(idx)
            else:
                if identifier.get("type") == idtype and identifier.get("id") == id:
                    remove.append(idx)
            idx += 1
        
        # sort the positions of the ids to remove, largest first
        remove.sort(reverse=True)
        
        # now remove them one by one (having the largest first means the lower indices
        # are not affected
        for i in remove:
            del self.bibjson["identifier"][i]
    
    @property
    def keywords(self):
        return self.bibjson.get("keywords", [])
    
    def add_keyword(self, keyword):
        if "keywords" not in self.bibjson:
            self.bibjson["keywords"] = []
        self.bibjson["keywords"].append(keyword)
    
    def set_keywords(self, keywords):
        self.bibjson["keywords"] = keywords
    
    def add_url(self, url, urltype=None):
        if "link" not in self.bibjson:
            self.bibjson["link"] = []
        urlobj = {"url" : url}
        if urltype is not None:
            urlobj["type"] = urltype
        self.bibjson["link"].append(urlobj)
    
    def get_urls(self, urltype=None):
        if urltype is None:
            return self.bibjson.get("link", [])
        
        urls = []
        for link in self.bibjson.get("link", []):
            if link.get("type") == urltype:
                urls.append(link.get("url"))
        return urls
    
    def add_subject(self, scheme, term, code=None):
        if "subject" not in self.bibjson:
            self.bibjson["subject"] = []
        sobj = {"scheme" : scheme, "term" : term}
        if code is not None:
            sobj["code"] = code
        self.bibjson["subject"].append(sobj)
    
    def subjects(self):
        return self.bibjson.get("subject", [])

############################################################################

####################################################################
## File upload model
####################################################################

class FileUpload(DomainObject):
    __type__ = "upload"
    
    def upload(self, filename, publisher):
        self.data["filename"] = filename
        self.data["publisher"] = publisher

####################################################################

####################################################################
## Account object and related classes
####################################################################

class Account(DomainObject, UserMixin):
    __type__ = 'account'

    @classmethod
    def pull_by_email(cls,email):
        res = cls.query(q='email:"' + email + '"')
        if res.get('hits',{}).get('total',0) == 1:
            return cls(**res['hits']['hits'][0]['_source'])
        else:
            return None
    
    @property
    def name(self):
        return self.data.get("name")
    
    def set_name(self, name):
        self.data["name"] = name
    
    @property
    def email(self):
        return self.data.get("email")

    def set_email(self, email):
        self.data["email"] = email

    def set_password(self, password):
        self.data['password'] = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.data['password'], password)
        
    @property
    def journal(self):
        return self.data.get("journal")
    
    def add_journal(self, jid):
        if jid in self.data.get("journal", []):
            return
        if "journal" not in self.data:
            self.data["journal"] = []
        self.data["journal"].append(jid)
    
    def remove_journal(self, jid):
        if "journal" not in self.data:
            return
        self.data["journal"].remove(jid)

    @property
    def is_super(self):
        return not self.is_anonymous() and self.id in app.config['SUPER_USER']
        
    def prep(self):
        self.data['last_updated'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

#########################################################################


#########################################################################
## Journal object and related classes
#########################################################################

# NOTE: DomainObject interferes with new style @property getter/setter
# so we can't use them here
class Journal(DomainObject):
    __type__ = "journal"
    CSV_HEADER = ["Title", "Title Alternative", "Identifier", "Publisher", "Language",
                    "ISSN", "EISSN", "Keyword", "Start Year", "End Year", "Added on date",
                    "Subjects", "Country", "Publication fee", "Further Information", 
                    "CC License", "Content in DOAJ"]
    
    @classmethod
    def find_by_issn(self, issn):
        q = JournalQuery()
        q.find_by_issn(issn)
        result = self.query(q=q.query)
        records = [Journal(**r.get("_source")) for r in result.get("hits", {}).get("hits", [])]
        return records
    
    def bibjson(self):
        if "bibjson" not in self.data:
            self.data["bibjson"] = {}
        return JournalBibJSON(self.data.get("bibjson"))

    def set_bibjson(self, bibjson):
        bibjson = bibjson.bibjson if isinstance(bibjson, JournalBibJSON) else bibjson
        self.data["bibjson"] = bibjson
    
    def history(self):
        histories = self.data.get("history", [])
        return [(h.get("date"), h.get("replaces"), h.get("isreplacedby"), JournalBibJSON(h.get("bibjson"))) for h in histories]
    
    def snapshot(self, replaces=None, isreplacedby=None):
        snap = deepcopy(self.data.get("bibjson"))
        self.add_history(snap, replaces=replaces, isreplacedby=isreplacedby)
    
    def add_history(self, bibjson, date=None, replaces=None, isreplacedby=None):
        bibjson = bibjson.bibjson if isinstance(bibjson, JournalBibJSON) else bibjson
        if date is None:
            date = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        snobj = {"date" : date, "bibjson" : bibjson}
        if replaces is not None:
            if isinstance(replaces, list):
                snobj["replaces"] = replaces
            else:
                snobj["replaces"] = [replaces]
        if isreplacedby is not None:
            if isinstance(isreplacedby, list):
                snobj["isreplacedby"] = isreplacedby
            else:
                snobj["isreplacedby"] = [replaces]
        if "history" not in self.data:
            self.data["history"] = []
        self.data["history"].append(snobj)
    
    def is_in_doaj(self):
        return self.data.get("admin", {}).get("in_doaj", False)
    
    def set_in_doaj(self, value):
        if "admin" not in self.data:
            self.data["admin"] = {}
        self.data["admin"]["in_doaj"] = value
    
    def application_status(self):
        return self.data.get("admin", {}).get("application_status")
    
    def set_application_status(self, value):
        if "admin" not in self.data:
            self.data["admin"] = {}
        self.data["admin"]["application_status"] = value
    
    def contacts(self):
        return self.data.get("admin", {}).get("contact", [])
        
    def add_contact(self, name, email):
        if "admin" not in self.data:
            self.data["admin"] = {}
        if "contact" not in self.data["admin"]:
            self.data["admin"]["contact"] = []
        self.data["admin"]["contact"].append({"name" : name, "email" : email})
    
    def add_note(self, note, date=None):
        if date is None:
            date = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        if "admin" not in self.data:
            self.data["admin"] = {}
        if "notes" not in self.data.get("admin"):
            self.data["admin"]["notes"] = []
        self.data["admin"]["notes"].append({"date" : date, "note" : note})
    
    def add_correspondence(self, message, date=None):
        if date is None:
            date = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        if "admin" not in self.data:
            self.data["admin"] = {}
        if "owner_correspondence" not in self.data.get("admin"):
            self.data["admin"]["owner_correspondence"] = []
        self.data["admin"]["owner_correspondence"].append({"date" : date, "note" : message})
    
    def _generate_index(self):
        # the index fields we are going to generate
        issns = []
        titles = []
        subjects = []
        schema_subjects = []
        schema_codes = []
        classification = []
        langs = []
        country = None
        license = []
        publisher = []
        
        # the places we're going to get those fields from
        cbib = self.bibjson()
        hist = self.history()
        
        # get the issns out of the current bibjson
        issns += cbib.get_identifiers(cbib.P_ISSN)
        issns += cbib.get_identifiers(cbib.E_ISSN)
        
        # get the title out of the current bibjson
        titles.append(cbib.title)
        
        # get the subjects and concatenate them with their schemes from the current bibjson
        for subs in cbib.subjects():
            scheme = subs.get("scheme")
            term = subs.get("term")
            subjects.append(term)
            schema_subjects.append(scheme + ":" + term)
            classification.append(term)
            if "code" in subs:
                schema_codes.append(scheme + ":" + subs.get("code"))
        
        # add the keywords to the non-schema subjects (but not the classification)
        subjects += cbib.keywords
        
        # now get the issns and titles out of the historic records
        for date, r, irb, hbib in hist:
            issns += hbib.get_identifiers(hbib.P_ISSN)
            issns += hbib.get_identifiers(hbib.E_ISSN)
            titles.append(hbib.title)
        
        # copy the languages
        if cbib.language is not None:
            langs = cbib.language
        
        # copy the country
        if cbib.country is not None:
            country = cbib.country
        
        # get the title of the license
        lic = cbib.get_license()
        if lic is not None:
            license.append(lic.get("title"))
        
        # copy the publisher/provider
        if cbib.publisher:
            publisher.append(cbib.publisher)
        if cbib.provider:
            publisher.append(cbib.provider)
        
        # deduplicate the lists
        issns = list(set(issns))
        titles = list(set(titles))
        subjects = list(set(subjects))
        schema_subjects = list(set(schema_subjects))
        classification = list(set(classification))
        license = list(set(license))
        publisher = list(set(publisher))
        langs = list(set(langs))
        schema_codes = list(set(schema_codes))
        
        # build the index part of the object
        self.data["index"] = {}
        if len(issns) > 0:
            self.data["index"]["issn"] = issns
        if len(titles) > 0:
            self.data["index"]["title"] = titles
        if len(subjects) > 0:
            self.data["index"]["subject"] = subjects
        if len(schema_subjects) > 0:
            self.data["index"]["schema_subject"] = schema_subjects
        if len(classification) > 0:
            self.data["index"]["classification"] = classification
        if len(publisher) > 0:
            self.data["index"]["publisher"] = publisher
        if len(license) > 0:
            self.data["index"]["license"] = license
        if len(langs) > 0:
            self.data["index"]["language"] = langs
        if country is not None:
            self.data["index"]["country"] = country
        if len(schema_codes) > 0:
            self.data["index"]["schema_code"] = schema_codes
    
    def _ensure_in_doaj(self):
        # switching active to false takes the item out of the DOAJ
        # though note that switching active to True does not put something IN the DOAJ
        if not self.bibjson().active:
            self.set_in_doaj(False)
    
    def prep(self):
        self._ensure_in_doaj()
        self._generate_index()
        self.data['last_updated'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    def save(self):
        self.prep()
        super(Journal, self).save()

    def csv(self, multival_sep=','):
        YES_NO = {True: 'Yes', False: 'No', None: '', '': ''}
        row = []
        c = self.data['bibjson']
        row.append(c.get('title', ''))
        row.append('') # in place of Title Alternative
        row.append( multival_sep.join(c.get('link', '')) )
        row.append(c.get('publisher', ''))
        row.append(c.get('language', ''))

        # we're following the old CSV format strictly for now, so only 1
        # ISSN allowed - below is the code for handling multiple ones

        # ISSN taken from Print ISSN
        # row.append( multival_sep.join([id_['id'] for id_ in c['identifier'] if id_['type'] == 'pissn']) )
        pissns = [id_['id'] for id_ in c.get('identifier', []) if id_['type'] == 'pissn']
        row.append(pissns[0] if len(pissns) > 0 else '') # just the 1st one

        # EISSN - the same as ISSN applies
        # row.append( multival_sep.join([id_['id'] for id_ in c['identifier'] if id_['type'] == 'eissn']) )
        eissns = [id_['id'] for id_ in c.get('identifier', []) if id_['type'] == 'eissn']
        row.append(eissns[0] if len(eissns) > 0 else '') # just the 1st one

        row.append( multival_sep.join(c.get('keywords', '')) )
        row.append(c.get('oa_start', {}).get('year'))
        row.append(c.get('oa_end', {}).get('year'))
        row.append(self.data.get('created_date', ''))
        row.append( multival_sep.join([subject['term'] for subject in c.get('subject', [])]) )
        row.append(c.get('country', ''))
        row.append(YES_NO[c.get('author_pays', '')])
        row.append(c.get('author_pays_url', ''))

        # for now, follow the strange format of the CC License column
        # that the old CSV had. Also, only take the first CC license we see!
        cc_licenses = [lic['type'][3:] for lic in c.get('license', []) if lic['type'].startswith('cc-')]
        row.append(cc_licenses[0] if len(cc_licenses) > 0 else '')
        
        row.append(YES_NO[c.get('active')])
        return row

class JournalBibJSON(GenericBibJSON):
    
    # journal-specific simple property getter and setters
    @property
    def alternative_title(self): return self.bibjson.get("alternative_title")
    @alternative_title.setter
    def alternative_title(self, val) : self.bibjson["alternative_title"] = val
    
    @property
    def author_pays_url(self): return self.bibjson.get("author_pays_url")
    @author_pays_url.setter
    def author_pays_url(self, val) : self.bibjson["author_pays_url"] = val
    
    @property
    def author_pays(self): return self.bibjson.get("author_pays")
    @author_pays.setter
    def author_pays(self, val) : self.bibjson["author_pays"] = val
    
    @property
    def country(self): return self.bibjson.get("country")
    @country.setter
    def country(self, val) : self.bibjson["country"] = val
    
    @property
    def publisher(self): return self.bibjson.get("publisher")
    @publisher.setter
    def publisher(self, val) : self.bibjson["publisher"] = val
    
    @property
    def provider(self): return self.bibjson.get("provider")
    @provider.setter
    def provider(self, val) : self.bibjson["provider"] = val
    
    @property
    def active(self): return self.bibjson.get("active")
    @active.setter
    def active(self, val) : self.bibjson["active"] = val
    
    # journal-specific complex part getters and setters
    
    @property
    def language(self): 
        return self.bibjson.get("language")
    
    def set_language(self, language):
        if isinstance(language, list):
            self.bibjson["language"] = language
        else:
            self.bibjson["language"] = [language]
    
    def add_language(self, language):
        if "language" not in self.bibjson:
            self.bibjson["language"] = []
        self.bibjson["language"].append(language)
    
    def set_license(self, licence_title, licence_type, url=None, version=None, open_access=None):
        if "license" not in self.bibjson:
            self.bibjson["license"] = []
        
        lobj = {"title" : licence_title, "type" : licence_type}
        if url is not None:
            lobj["url"] = url
        if version is not None:
            lobj["version"] = version
        if open_access is not None:
            lobj["open_access"] = open_access
        
        self.bibjson["license"].append(lobj)
    
    def get_license(self):
        return self.bibjson.get("license", [None])[0]
    
    def set_open_access(self, open_access):
        if "license" not in self.bibjson:
            self.bibjson["license"] = []
        if len(self.bibjson["license"]) == 0:
            lobj = {"open_access" : open_access}
            self.bibjson["license"].append(lobj)
        else:
            self.bibjson["license"][0]["open_access"] = open_access
    
    def set_oa_start(self, year=None, volume=None, number=None):
        oaobj = {}
        if year is not None:
            oaobj["year"] = year
        if volume is not None:
            oaobj["volume"] = volume
        if number is not None:
            oaobj["number"] = number
        self.bibjson["oa_start"] = oaobj
    
    def set_oa_end(self, year=None, volume=None, number=None):
        oaobj = {}
        if year is not None:
            oaobj["year"] = year
        if volume is not None:
            oaobj["volume"] = volume
        if number is not None:
            oaobj["number"] = number
        self.bibjson["oa_end"] = oaobj

class JournalQuery(object):
    """
    wrapper around the kinds of queries we want to do against the journal type
    """
    issn_query = {
        "query": {
        	"bool": {
            	"must": [
                	{
                    	"term" :  { "index.issn.exact" : "<issn>" }
                    }
                ]
            }
        }
    }
    
    def __init__(self):
        self.query = None
    
    def find_by_issn(self, issn):
        self.query = deepcopy(self.issn_query)
        self.query["query"]["bool"]["must"][0]["term"]["index.issn.exact"] = issn

############################################################################

############################################################################
## Suggestion object and related classes
############################################################################

class Suggestion(Journal):
    __type__ = "suggestion"
    
    def _set_suggestion_property(self, name, value):
        if "suggestion" not in self.data:
            self.data["suggestion"] = {}
        self.data["suggestion"][name] = value
    
    def description(self): return self.data.get("suggestion", {}).get("description")
    
    def set_description(self, value): self._set_suggestion_property("description", value)
    
    def suggested_by_owner(self): return self.data.get("suggestion", {}).get("suggested_by_owner")
    
    def set_suggested_by_owner(self, value): self._set_suggestion_property("suggested_by_owner", value)
    
    def suggested_on(self): return self.data.get("suggestion", {}).get("suggested_on")
    
    def set_suggested_on(self, value): self._set_suggestion_property("suggested_on", value)
    
    def suggester(self):
        return self.data.get("suggestion", {}).get("suggester")
        
    def set_suggester(self, name, email):
        if "suggestion" not in self.data:
            self.data["suggestion"] = {}
        self.data["suggestion"]["suggester"] = {"name" : name, "email" : email}

############################################################################

####################################################################
# Article and related classes
####################################################################

class Article(DomainObject):
    __type__ = "article"
    
    def bibjson(self):
        if "bibjson" not in self.data:
            self.data["bibjson"] = {}
        return ArticleBibJSON(self.data.get("bibjson"))

    def set_bibjson(self, bibjson):
        bibjson = bibjson.bibjson if isinstance(bibjson, ArticleBibJSON) else bibjson
        self.data["bibjson"] = bibjson
    
    def history(self):
        hs = self.data.get("history", [])
        tuples = []
        for h in hs:
            tuples.append((h.get("date"), ArticleBibJSON(h.get("bibjson"))))
        return tuples
    
    def snapshot(self):
        snap = deepcopy(self.data.get("bibjson"))
        self.add_history(snap)
    
    def add_history(self, bibjson, date=None):
        bibjson = bibjson.bibjson if isinstance(bibjson, ArticleBibJSON) else bibjson
        if date is None:
            date = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        snobj = {"date" : date, "bibjson" : bibjson}
        if "history" not in self.data:
            self.data["history"] = []
        self.data["history"].append(snobj)
    
    def is_in_doaj(self):
        return self.data.get("admin", {}).get("in_doaj", False)
    
    def set_in_doaj(self, value):
        if "admin" not in self.data:
            self.data["admin"] = {}
        self.data["admin"]["in_doaj"] = value
    
    def _generate_index(self):
        # the index fields we are going to generate
        issns = []
        subjects = []
        schema_subjects = []
        schema_codes = []
        classification = []
        langs = []
        country = None
        license = []
        publisher = []
        
        # the places we're going to get those fields from
        cbib = self.bibjson()
        hist = self.history()
        
        # get the issns out of the current bibjson
        issns += cbib.get_identifiers(cbib.P_ISSN)
        issns += cbib.get_identifiers(cbib.E_ISSN)
        
        # now get the issns out of the historic records
        for date, hbib in hist:
            issns += hbib.get_identifiers(hbib.P_ISSN)
            issns += hbib.get_identifiers(hbib.E_ISSN)
        
        # get the subjects and concatenate them with their schemes from the current bibjson
        for subs in cbib.subjects():
            scheme = subs.get("scheme")
            term = subs.get("term")
            subjects.append(term)
            schema_subjects.append(scheme + ":" + term)
            classification.append(term)
            if "code" in subs:
                schema_codes.append(scheme + ":" + subs.get("code"))
        
        # copy the languages
        if cbib.journal_language is not None:
            langs = cbib.journal_language
        
        # copy the country
        if cbib.journal_country is not None:
            country = cbib.journal_country
        
        # get the title of the license
        lic = cbib.get_journal_license()
        if lic is not None:
            license.append(lic.get("title"))
        
        # copy the publisher/provider
        if cbib.publisher:
            publisher.append(cbib.publisher)
        
        # deduplicate the list
        issns = list(set(issns))
        subjects = list(set(subjects))
        schema_subjects = list(set(schema_subjects))
        classification = list(set(classification))
        license = list(set(license))
        publisher = list(set(publisher))
        langs = list(set(langs))
        schema_codes = list(set(schema_codes))
        
        # work out what the date of publication is
        date = cbib.get_publication_date()
        
        # build the index part of the object
        self.data["index"] = {}
        if len(issns) > 0:
            self.data["index"]["issn"] = issns
        if date != "":
            self.data["index"]["date"] = date
        if len(subjects) > 0:
            self.data["index"]["subject"] = subjects
        if len(schema_subjects) > 0:
            self.data["index"]["schema_subject"] = schema_subjects
        if len(classification) > 0:
            self.data["index"]["classification"] = classification
        if len(publisher) > 0:
            self.data["index"]["publisher"] = publisher
        if len(license) > 0:
            self.data["index"]["license"] = license
        if len(langs) > 0:
            self.data["index"]["language"] = langs
        if country is not None:
            self.data["index"]["country"] = country
        if schema_codes > 0:
            self.data["index"]["schema_code"] = schema_codes
    
    def prep(self):
        self._generate_index()
        self.data['last_updated'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    def save(self):
        self._generate_index()
        super(Article, self).save()
    
class ArticleBibJSON(GenericBibJSON):
    
    # article-specific simple getters and setters
    @property
    def year(self): return self.bibjson.get("year")
    @year.setter
    def year(self, val) : self.bibjson["year"] = val
    
    @property
    def month(self): return self.bibjson.get("month")
    @month.setter
    def month(self, val) : self.bibjson["month"] = val
    
    @property
    def start_page(self): return self.bibjson.get("start_page")
    @start_page.setter
    def start_page(self, val) : self.bibjson["start_page"] = val
    
    @property
    def end_page(self): return self.bibjson.get("end_page")
    @end_page.setter
    def end_page(self, val) : self.bibjson["end_page"] = val
    
    @property
    def abstract(self): return self.bibjson.get("abstract")
    @abstract.setter
    def abstract(self, val) : self.bibjson["abstract"] = val
    
    # article-specific complex part getters and setters
    
    def _set_journal_property(self, prop, value):
        if "journal" not in self.bibjson:
            self.bibjson["journal"] = {}
        self.bibjson["journal"][prop] = value
    
    @property
    def volume(self):
        return self.bibjson.get("journal", {}).get("volume")
    
    @volume.setter
    def volume(self, value):
        self._set_journal_property("volume", value)
    
    @property
    def number(self):
        return self.bibjson.get("journal", {}).get("number")
    
    @number.setter
    def number(self, value):
        self._set_journal_property("number", value)
    
    @property
    def journal_title(self):
        return self.bibjson.get("journal", {}).get("title")
    
    @journal_title.setter
    def journal_title(self, title):
        self._set_journal_property("title", title)
    
    @property
    def journal_language(self):
        return self.bibjson.get("journal", {}).get("language")
    
    @journal_language.setter
    def journal_language(self, lang):
        self._set_journal_property("language", lang)
    
    @property
    def journal_country(self):
        return self.bibjson.get("journal", {}).get("country")
    
    @journal_country.setter
    def journal_country(self, country):
        self._set_journal_property("country", country)
    
    @property
    def publisher(self):
        return self.bibjson.get("journal", {}).get("publisher")
    
    @publisher.setter
    def publisher(self, value):
        self._set_journal_property("publisher", value)
        
    def add_author(self, name):
        if "author" not in self.bibjson:
            self.bibjson["author"] = []
        self.bibjson["author"].append({"name" : name})
    
    @property
    def author(self):
        return self.bibjson.get("author", [])
    
    def set_journal_license(self, licence_title, licence_type, url=None, version=None, open_access=None):
        lobj = {"title" : licence_title, "type" : licence_type}
        if url is not None:
            lobj["url"] = url
        if version is not None:
            lobj["version"] = version
        if open_access is not None:
            lobj["open_access"] = open_access
        
        self._set_journal_property("license", [lobj])
    
    def get_journal_license(self):
        return self.bibjson.get("journal", {}).get("license", [None])[0]
    
    def get_publication_date(self):
        # work out what the date of publication is
        date = ""
        if self.year is not None:
            # fix 2 digit years
            if len(self.year) == 2:
                if int(self.year) <=13:
                    self.year = "20" + self.year
                else:
                    self.year = "19" + self.year
                    
            # if we still don't have a 4 digit year, forget it
            if len(self.year) != 4:
                return date
            
            # build up our proposed datestamp
            date += str(self.year)
            if self.month is not None:
                try:
                    if len(self.month) == 1:
                        date += "-0" + str(self.month)
                    else:
                        date += "-" + str(self.month)
                except:
                    # FIXME: months are in all sorts of forms, we can only handle 
                    # numeric ones right now
                    date += "-01" 
            else:
                date += "-01"
            date += "-01T00:00:00Z"
            
            # attempt to confirm the format of our datestamp
            try:
                datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
            except:
                return ""
        return date

####################################################################

####################################################################
## OAI-PMH Record Objects
####################################################################

class OAIPMHRecord(object):
    earliest = {
	        "query" : {
            	"bool" : {
                	"must" : [
                	    {"term" : {"admin.in_doaj" : True}}
                	]
                }
            },
            "size" : 0,
            "facets" : {
            	"earliest" : {
                	"terms" : {
                    	"field" : "last_updated",
                        "order" : "term"
                    }
                }
            }
        }
    
    sets = {
	    "query" : {
        	"bool" : {
            	"must" : [
            	    {"term" : {"admin.in_doaj" : True}}
            	]
            }
        },
        "size" : 0,
        "facets" : {
        	"sets" : {
            	"terms" : {
                	"field" : "index.schema_subject.exact",
                    "order" : "term",
                    "size" : 100000
                }
            }
        }
    }
    
    records = {
	    "query" : {
        	"bool" : {
            	"must" : [
            	    {"term" : {"admin.in_doaj" : True}}
            	]
            }
        },
        "from" : 0,
        "size" : 25
    }
    
    set_limit = {"term" : { "index.schema_subject.exact" : "<set name>" }}
    range_limit = { "range" : { "last_updated" : {"gte" : "<from date>", "lte" : "<until date>"} } }
    created_sort = {"last_updated" : {"order" : "desc"}}
    
    def earliest_datestamp(self):
        result = self.query(q=self.earliest)
        dates = [t.get("term") for t in result.get("facets", {}).get("earliest", {}).get("terms", [])]
        for d in dates:
            if d > 0:
                return datetime.fromtimestamp(d / 1000.0).strftime("%Y-%m-%dT%H:%M:%SZ")
        return None
    
    def identifier_exists(self, identifier):
        obj = self.pull(identifier)
        return obj is not None
    
    def list_sets(self):
        result = self.query(q=self.sets)
        sets = [t.get("term") for t in result.get("facets", {}).get("sets", {}).get("terms", [])]
        return sets
    
    def list_records(self, from_date=None, until_date=None, oai_set=None, list_size=None, start_number=None):
        q = deepcopy(self.records)
        if from_date is not None or until_date is not None or oai_set is not None:
            
            if oai_set is not None:
                s = deepcopy(self.set_limit)
                s["term"]["index.schema_subject.exact"] = oai_set
                q["query"]["bool"]["must"].append(s)
            
            if until_date is not None or from_date is not None:
                d = deepcopy(self.range_limit)
                
                if until_date is not None:
                    d["range"]["last_updated"]["lte"] = until_date
                else:
                    del d["range"]["last_updated"]["lte"]
                
                if from_date is not None:
                    d["range"]["last_updated"]["gte"] = from_date
                else:
                    del d["range"]["last_updated"]["gte"]
                
                q["query"]["bool"]["must"].append(d)
        
        if list_size is not None:
            q["size"] = list_size
            
        if start_number is not None:
            q["from"] = start_number
        
        q["sort"] = [deepcopy(self.created_sort)]
        
        # do the query
        # print json.dumps(q)
        results = self.query(q=q)
        
        total = results.get("hits", {}).get("total", 0)
        return total, [hit.get("_source") for hit in results.get("hits", {}).get("hits", [])]
        

class OAIPMHArticle(OAIPMHRecord, Article):
    def list_records(self, from_date=None, until_date=None, oai_set=None, list_size=None, start_number=None):
        total, results = super(OAIPMHArticle, self).list_records(from_date=from_date, 
            until_date=until_date, oai_set=oai_set, list_size=list_size, start_number=start_number)
        return total, [Article(**r) for r in results]
    
    def pull(self, identifier):
        # override the default pull, as we care about whether the item is in_doaj
        record = super(OAIPMHArticle, self).pull(identifier)
        if record.is_in_doaj():
            return record
        return None

class OAIPMHJournal(OAIPMHRecord, Journal):
    def list_records(self, from_date=None, until_date=None, oai_set=None, list_size=None, start_number=None):
        total, results = super(OAIPMHJournal, self).list_records(from_date=from_date, 
            until_date=until_date, oai_set=oai_set, list_size=list_size, start_number=start_number)
        return total, [Journal(**r) for r in results]
    
    def pull(self, identifier):
        # override the default pull, as we care about whether the item is in_doaj
        record = super(OAIPMHJournal, self).pull(identifier)
        if record.is_in_doaj():
            return record
        return None

####################################################################

####################################################################
## Atom Record Object
####################################################################

class AtomRecord(Journal):
    records = {
	    "query" : {
        	"bool" : {
            	"must" : [
            	    {"term" : {"admin.in_doaj" : True}},
            	    { "range" : { "last_updated" : {"gte" : "<from date>"} } }
            	]
            }
        },
        "size" : 20,
        "sort" : {"last_updated" : {"order" : "desc"}}
    }
    
    def list_records(self, from_date, list_size):
        q = deepcopy(self.records)
        q["query"]["bool"]["must"][1]["range"]["last_updated"]["gte"] = from_date
        q["size"] = list_size
        
        # do the query
        # print json.dumps(q)
        results = self.query(q=q)
        
        return [AtomRecord(**hit.get("_source")) for hit in results.get("hits", {}).get("hits", [])]

class JournalArticle(DomainObject):
    __type__ = 'journal,article'
    __readonly__ = True  # TODO actually heed this attribute in all DomainObject methods which modify data
