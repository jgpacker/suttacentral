"""SuttaCentral In-Memory Module.

Example:
    >>> from sc import scimm
    >>> imm = scimm.imm()
    >>> imm.suttas.get('dn1')
    < Sutta: "Brahmajāla"
        uid=dn1,
        ... >
"""

import csv
import time
import math
import regex
import hashlib
import logging
import threading
from bisect import bisect
from datetime import datetime
from collections import OrderedDict, defaultdict, namedtuple

import sc
from sc import config, textfunctions, I18N
from sc.classes import *
from sc.util import ScCsvDialect

logger = logging.getLogger(__name__)

def numsortkey(input, index=0):
    """ Numerical sort. Handles identifiers well.

    If variable lengths ranges are involved (i.e. 1.2 vs 1.11.111) see
    'natsortkey', which is about 20x slower but handles such cases
    gracefully.
    """
    if type(input) is str:
        string = input
    else:
        string = input[index]
        if string is None:
            return []
    return ( [int(a) if a.isnumeric() else a
                   for a in regex.split(r'(\d+)', string)] )



def table_reader(tablename):
    """ Like csv.DictReader but returns named tuples (2x faster also) """
    with (sc.table_dir / (tablename + '.csv')).open('r',
              encoding='utf-8', newline='') as f:
        reader = csv.reader(f, dialect=ScCsvDialect)
        field_names = next(reader)
        NtName = '_' + tablename.title()
        NT = namedtuple(NtName, field_names)
        globals()[NtName] = NT
        for lineno, row in enumerate(reader):
            if not any(row): # Drop entirely blank lines
                continue
            if row[0].startswith('#'):
                continue
            try:
                yield NT._make(row)
            except TypeError as e:
                raise TypeError('Error on line {} in table {}, ({})'.format(
                    lineno, tablename, e))

class _Imm:
    _uidlangcache = {}
    def __init__(self, timestamp):
        self.build()
        self.build_parallels_data()
        self.build_parallels()
        self.build_vinaya_rules()
        self.build_search_data()
        self.timestamp = timestamp
        self.build_time = datetime.now()
        logger.info('building i18n data')
        self.i18n = I18N.I18N()
        self.i18n.read_data()
    
    def __call__(self, uid):
        if uid in self.collections:
            return self.collections[uid]
        elif uid in self.divisions:
            return self.divisions[uid]
        elif uid in self.subdivisions:
            return self.subdivisions[uid]
        elif uid in self.suttas:
            return self.suttas[uid]
    
    def uid_to_acro(self, uid):
        components = regex.findall(r'\p{alpha}+|\d+(?:\.\d+)*', uid)
        return ' '.join(self._uid_to_acro_map.get(c) or c.upper() for c in components)
        
    def uid_to_name(self, uid):
        components = regex.findall(r'\p{alpha}+|\d+(?:\.\d+)*', uid)
        return ' '.join(self._uid_to_name_map.get(c) or c.upper() for c in components)
    
    def build(self):
        """ Build the sutta central In Memory Model

        This starts from the highest level (i.e. collection) and works to
        the lowest level (i.e. parallels - the relationship between suttas)
        Since it is fully navigitable both up and down this means some
        elements can't be populated initially. This means that suttas
        insert themselves into the subdivision where they belong.

        Some tables are indexed as dicts, with the key being the uid.
        These include:
        collection, division, subdivision, sutta, language
        
        When classes are contained within a class, for example, suttas in
        a subdivision, this is always represented by a list. That list will
        be sorted appropriately and can be directly outputted, generally
        without any need for filtering or sorting.

        When an attribute is a list or dict, the name always end in an 's'
        for example:
        imm.suttas['sn1.1'].subdivision.division.subdivisions[0].suttas[0]

        Some things, such as parallels, are not indexed at all, and are
        only accessable as attributes of the relevant suttas.
        
        The imm also examines the file system. The fully qualified path to a 
        text can be acquired using:
        imm.text_paths[lang][uid]

        """
        
        # Load uid to acro map
        self._uid_to_acro_map = {}
        self._uid_to_name_map = {}
        for row in table_reader('uid_expansion'):
            self._uid_to_acro_map[row.uid] = row.acro
            self._uid_to_name_map[row.uid] = row.name
        
        # Build Pitakas
        self.pitakas = OrderedDict()
        for row in table_reader('pitaka'):
            self.pitakas[row.uid] = Pitaka(uid=row.uid, name=row.name, always_full=row.always_full)

        # Build Sects
        self.sects = OrderedDict()
        for row in table_reader('sect'):
            self.sects[row.uid] = Sect(uid=row.uid, name=row.name)

        # Build Languages (indexed by id)
        self.languages = OrderedDict()
        for row in table_reader('language'):
            self.languages[row.uid] = Language(
                uid=row.uid,
                name=row.name,
                iso_code=row.iso_code,
                isroot=row.isroot,
                priority=row.priority,
                collections=[],
                )
        
        # Note that one isocode can map to multiple languages
        # for example zh modern/ancient
        self.isocode_to_language = {}
        for language in self.languages.values():
            if language.iso_code not in self.isocode_to_language:
                self.isocode_to_language[language.iso_code] = []
            self.isocode_to_language[language.iso_code].append(language)
        
        # Gather up text refs:
        # From filesystem (This also returns important text_paths variable)
        self.text_paths_by_lang, text_refs = self.scan_text_dir()
        # Produce an alternative nesting
        # (The raw path data can be used to generate TextRef objects
        # on the fly rather than in advance, this is used for vinaya)
        text_paths_by_uid = {}
        for lang, d in self.text_paths_by_lang.items():
            for uid, path in d.items():
                if not uid in text_paths_by_uid:
                    text_paths_by_uid[uid] = {}
                text_paths_by_uid[uid][lang] = path
        self.text_paths_by_uid = text_paths_by_uid
        
        # Make a copy, note: we want copy of lists, not refs to them!
        local_text_refs = {key: value[:] for key, value in text_refs.items()}
        
        # From external_text table
        for row in table_reader('external_text'):
            text_refs[row.sutta_uid].append( TextRef(lang=self.languages[row.language], abstract=row.abstract, url=row.url, priority=row.priority) )
        
        collections = []
        for i, row in enumerate(table_reader('collection')):
            if row.sect_uid:
                sect = self.sects[row.sect_uid]
            else:
                sect = None
            collection = Collection(
                uid=row.uid,
                name=row.name,
                abbrev_name=row.abbrev_name,
                lang=self.languages[row.language],
                sect=sect,
                pitaka=self.pitakas[row.pitaka_uid],
                menu_seq=i,
                divisions=[] # Populate later
                )
            collections.append(collection)

        # Sort collections by menu_seq
        collections.sort(key=Collection.sort_key)

        self.collections = OrderedDict()
        for collection in collections:
            self.collections[collection.uid] = collection
            self.languages[collection.lang.uid].collections.append(collection)

        # Build divisions (indexed by uid)
        self.divisions = OrderedDict()
        for i, row in enumerate(table_reader('division')):
            collection = self.collections[row.collection_uid]
            try:
                text_ref = text_refs[row.uid][0]
            except (KeyError, IndexError):
                text_ref = None
            division = Division(
                uid=row.uid,
                name=row.name,
                alt_name=row.alt_name,
                acronym=row.acronym or self.uid_to_acro(row.uid),
                subdiv_ind=row.subdiv_ind,
                menu_seq=i,
                menu_gwn_ind=bool(row.menu_gwn_ind),
                text_ref=text_ref,
                collection=collection,
                subdivisions=[], # Populate later
            )
            self.divisions[row.uid] = division
            # Populate collections
            collection.divisions.append(division)

        # Sort divisions within collections by menu_seq
        for collection in self.collections.values():
            collection.divisions.sort(key=Division.sort_key)

        # Build subdivisions (indexed by uid)
        self.subdivisions = OrderedDict()
        self.nosubs = set()
        for i, row in enumerate(table_reader('subdivision')):
            subdivision = Subdivision(
                uid=row.uid,
                acronym=row.acronym,
                division=self.divisions[row.division_uid],
                name=row.name,
                vagga_numbering_ind=row.vagga_numbering_ind,
                order=i,
                vaggas=[], # Populate later
                suttas=[] # Populate later
            )
            self.subdivisions[row.uid] = subdivision
            if row.uid.endswith('-nosub'):
                self.nosubs.add(row.uid[:-6])
            # populate divisions.subdivisions
            self.divisions[row.division_uid].subdivisions.append(subdivision)
        
        for division in self.divisions.values():
            if not division.subdivisions:
                subdivision = Subdivision(
                                uid=None,
                                acronym=None,
                                division=division,
                                name=None,
                                vagga_numbering_ind=False,
                                order=9000,
                                vaggas=[],
                                suttas=[])
                division.subdivisions.append(subdivision)
                self.subdivisions[division.uid] = subdivision
        
        # Build vaggas
        self.vaggas = OrderedDict()
        for row in table_reader('vagga'):
            vagga = Vagga(
                subdivision=self.subdivisions[row.subdivision_uid],
                number=row.number,
                name=row.name,
                suttas=[], # Populate later
            )
            self.vaggas[(row.subdivision_uid, row.number)] = vagga
            # Populate subdivision.vaggas
            vagga.subdivision.vaggas.append(vagga)
        
        for subdivision in self.subdivisions.values():
            if not subdivision.vaggas:
                subdivision.vaggas.append(Vagga(
                    subdivision=subdivision,
                    number=0,
                    name=None,
                    suttas=[]))
        
        # Load biblio entries (Not into an instance variable)
        biblios = {}
        for row in table_reader('biblio'):
            biblios[row.uid] = BiblioEntry(
                uid=row.uid,
                name=row.name,
                text=row.text)
        
        # Build suttas (indexed by uid)
        suttas = []
        for row in table_reader('sutta'):
            uid = row.uid
            volpage = row.volpage.split('//')
            acro = row.acronym.split('//')
            if not acro[0]:
                acro[0] = self.uid_to_acro(uid)
            
            lang = self.languages[row.language]
            
            text_ref = None;
            translations = []
            translangs = set()
            if uid in text_refs:
                for ref in text_refs[uid]:
                    if ref.lang == lang:
                        text_ref = ref
                    else:
                        translations.append(ref)
                        translangs.add(ref.lang.uid)
            variants = []
            m = regex.match(r'(.*?)\.?(\d+[a-z]?)$', uid)
            if m:
                variants.append((m[1], m[2]))
            m = regex.match(r'(.*?)((\d+)-\d+$)', uid)
            if m:
                variants.append((m[1] + m[3], m[2]))
            for sub_uid, bookmark in variants:
                if sub_uid in local_text_refs:
                    for ref in local_text_refs[sub_uid]:
                        ref = TextRef(lang=ref.lang,
                                    abstract=ref.abstract,
                                    url=ref.url.split('#')[0] + '#' + bookmark,
                                    priority=0,
                                    )
                        if ref.lang == lang:
                            if not text_ref:
                                text_ref = ref
                        elif ref.lang.uid not in translangs:
                            translations.append(ref)
                
            translations.sort(key=TextRef.sort_key)
            
            subdivision = self.subdivisions[row.subdivision_uid]
            
            if row.vagga_number:
                vagga_number = int(row.vagga_number)
                vagga = subdivision.vaggas[vagga_number - 1]
            else:
                vagga_number = 0
                vagga = subdivision.vaggas[0]
            
            m = regex.search(r'(?r)\d+', row.uid)
            if m:
                number = int(m[0])
            else:
                number = 9999
            
            biblio_entry = None
            if row.biblio_uid:
                biblio_entry = biblios.get(row.biblio_uid)
            
            sutta = Sutta(
                uid=row.uid,
                acronym=acro[0],
                alt_acronym=acro[1] if len(acro) > 1 else None,
                name=row.name,
                vagga_number=vagga_number,
                lang=lang,
                subdivision=subdivision,
                vagga=vagga,
                number=number,
                number_in_vagga=row.number_in_vagga,
                volpage_info=volpage[0],
                alt_volpage_info=volpage[1] if len(volpage) > 1 else None,
                biblio_entry=biblio_entry,
                text_ref=text_ref,
                translations=translations,
                parallels=[],
            )
            suttas.append( (uid, sutta) )
        
        suttas = sorted(suttas, key=numsortkey)
        
        
        
        self.suttas = OrderedDict(suttas)
        
        # Populate subdivisions.suttas
        for sutta in self.suttas.values():
            sutta.subdivision.suttas.append(sutta)
            sutta.vagga.suttas.append(sutta)
        
    def build_parallels_data(self):
        
        fulls = defaultdict(set)
        partials = defaultdict(set)
        indirects = defaultdict(set)
        # initially we operate purely on ids using id, footnote tuples

        #Populate partial and full parallels
        for row in table_reader('correspondence'):
            if row.partial:
                partials[row.sutta_uid].add( (row.other_sutta_uid, row.footnote) )
                partials[row.other_sutta_uid].add( (row.sutta_uid, row.footnote) )
            else:
                fulls[row.sutta_uid].add( (row.other_sutta_uid, row.footnote) )
                fulls[row.other_sutta_uid].add( (row.sutta_uid, row.footnote) )

        # Populate indirect full parallels
        for id, parallels in fulls.items():
            for pid, footnote in parallels:
                if pid in fulls:
                    indirects[id].update(fulls[pid])

        for id, parallels in indirects.items():
            # Remove self and fulls
            indirects[id] -= set(a for a in indirects[id] if a[0] == id)

        return {
            'fulls': fulls.items(),
            'indirects': indirects.items(),
            'partials': partials.items(),
            }
    
    def build_parallels(self):
        parallels_data = self.build_parallels_data()
        fulls = parallels_data['fulls']
        indirects = parallels_data['indirects']
        partials = parallels_data['partials']
        
        for sutta_uid, parallels in fulls:
            sutta = self.suttas[sutta_uid]
            for p_uid, note in parallels:
                p_sutta = self.suttas[p_uid]
                sutta.parallels.append(Parallel(p_sutta, False, False, note))
                
        for sutta_uid, parallels in indirects:
            sutta = self.suttas[sutta_uid]
            for p_uid, note in parallels:
                p_sutta = self.suttas[p_uid]
                sutta.parallels.append(Parallel(p_sutta, False, True, note))

        for sutta_uid, parallels in partials:
            sutta = self.suttas[sutta_uid]
            for p_uid, note in parallels:
                p_sutta = self.suttas[p_uid]
                sutta.parallels.append(Parallel(p_sutta, True, False, note))

        for sutta in self.suttas.values():
            sutta.parallels.sort(key=Parallel.sort_key)
    
    def build_vinaya_rules(self):
        """ Generate a cleaned up form of the table data
        
        But it is not unfolded as completly as for suttas.
        
        """
        
        start = time.time()
        vinaya_rules = {}
        for i, row in enumerate(table_reader('vinaya_rules')):
            uid = row.uid
            rule = VinayaRule(
                uid=uid,
                volpage_info=row.volpage_info,
                imm=self,
            )
            
            subdivision = rule.subdivision
            subdivision.suttas.append(rule)
            
            subdivision.vaggas[0].suttas.append(rule)
            
            self.suttas[uid] = rule
            vinaya_rules[uid] = rule
        
        def normalize_uid(uid):
            return uid.replace('#', '-').replace('*', '')
        
        org_by_rule = list(table_reader('vinaya'))
        
        by_school = []
        for i, column in enumerate(zip(*org_by_rule)): #rotate
            if i == 0:
                by_school.append(column)
            else:
                division_uid = column[0]
                division = self.divisions[division_uid]
                division_negated_parallel = NegatedParallel(
                    division=division)
                division_maybe_parallel = MaybeParallel(
                    division=division)
                new_column = []
                by_school.append(new_column)
                for j, uid in enumerate(column):
                    if j <= 1:
                        new_column.append(uid)
                    else:
                        if not uid:
                            new_column.append(division_negated_parallel)
                        elif uid == '?':
                            new_column.append(division_maybe_parallel)
                        else:
                            rule = vinaya_rules[normalize_uid(uid)]
                            rule.ref_uid = uid
                            new_column.append(rule)
        
        by_rule = list(zip(*by_school))
        self.by_school = by_school
        self.by_rule = by_rule
        
        for row in by_rule[2:]:
            for rule in row[1:]:
                if isinstance(rule, VinayaRule):
                    rule._rule_row = row
        
        print('Vinaya generation took {}s'.format(time.time()-start))
        return
        
        # We update empties
        for column in by_school[1:]:
            div_uid = column[0]
            for i, uid in enumerate(column):
                if i <= 1:
                    continue
                if uid == '':
                    column[i] = div_uid + no_ll
                elif uid == '?':
                    column[i] = div_uid + maybe_ll
        
        by_rule = list(zip(*by_school))
        
        vinaya_parallels = defaultdict(dict)
        hrefs = {}
        for row in by_rule[1:]:
            row = row[1:]
            for uid in row:
                if uid not in {'', '?'}:
                    hrefs[uid] = uid.replace('*', '')
                for oth_uid in row:
                    if uid != oth_uid:
                        vinaya_parallels[uid][oth_uid] = 1
        
        def remove_duplicates(inlist):
            out = []
            seen = set()
            for e in inlist:
                if e in seen:
                    continue
                seen.add(e)
                out.append(normalize_uid(e))
            return out
        
        self.vinaya_parallels = {normalize_uid(k): remove_duplicates(v) 
                                    for k, v
                                    in vinaya_parallels.items()}
        
        self.vinaya_text_hrefs = hrefs
        
        
    def build_search_data(self):
        """ Build useful search data.

        Note that the size of the data is somewhat less than 2mb """
        
        suttastringsU = []
        seen = set()
        for sutta in self.suttas.values():
            if isinstance(sutta, VinayaRule):
                if sutta.name in seen:
                    continue
                seen.add(sutta.name)
            name = sutta.name.lower()
            suttastringsU.append("  {}  ".format("  ".join(
                                [sutta.uid,
                                sutta.lang.iso_code,
                                sutta.acronym,
                                sutta.alt_acronym or '',
                                name,
                                textfunctions.codely(name),
                                textfunctions.plainly(name),
                                sutta.volpage_info,
                                sutta.alt_volpage_info or '',
                                "  ".join( t.lang.iso_code
                                    for t in sutta.translations,) or '',]))
                                )
        suttastrings = [s.lower() for s in suttastringsU]
        # Only simplify the name.
        suttanamesimplified = (["  {}  ".format(
            textfunctions.simplify(sutta.name, sutta.lang.iso_code))
            for sutta in self.suttas.values()])

        self.searchstrings = list(zip(self.suttas.values(), suttastrings, suttastringsU, suttanamesimplified))
       
    def scan_text_dir(self):
        """ Provides fully qualified paths for all texts.
        
        Texts are keyed [lang][uid]
        Note that subfolders within a langroot are ignored. For example a file:
        text_dir/pi/sn/56/sn56.11.html would be found by the key ('pi', 'sn56.11'),
        thus subfolders exist solely for ease of file organization.
        """
        import glob
        text_paths = {}
        text_refs = defaultdict(list)
        
        for full_path in sc.text_dir.glob('**/*.html'):
            relative_path = full_path.relative_to(sc.text_dir)
            lang = relative_path.parts[0]
            if lang not in text_paths:
                text_paths[lang] = {}
            uid = relative_path.name.replace('.html', '')
            assert uid not in text_paths[lang]
            text_paths[lang][uid] = str(relative_path)

            author = self.get_text_author(full_path)
            url = Sutta.canon_url(lang_code=lang, uid=uid)
            text_refs[uid].append( TextRef(self.languages[lang], author, url, 0) )

            # In the case of a sutta range, we create new entries
            # for the entire range. Unneeded entries will be gc'd
            m = regex.match(r'(.*?)(\d+)-(\d+)$', uid)
            if m:
                range_start, range_end = int(m[2]), int(m[3])

                for i in range(range_start, range_end + 1):
                    try:
                        text_refs[m[1]+str(i)].append( TextRef(self.languages[lang], author, url + '#' + str(i), 0))                            
                    except KeyError:
                        globals().update(locals())
                        raise

        return (text_paths, text_refs)
    
    def get_text_path(self, lang, uid):
        try:
            return self.text_paths[lang][uid]
        except KeyError:
            return None
    
    _author_search = regex.compile(r'''(?s)<meta[^>]+author=(?|"(.*?)"|'(.*?)')''').search
    
    def get_text_nextprev(self, uid, language_code):
        try:
            uids = self._uidlangcache[language_code]
        except KeyError:
            uids = sorted(self.text_paths_by_lang[language_code],
                key=sc.util.humansortkey)
            self._uidlangcache[language_code] = uids
            # The cache is eliminated upon imm regeneration.
        
        # This is a horrible way to find an index but can still run 
        # 4000 times a second on the largest collections :).
        try:
            i = uids.index(uid)
        except ValueError:
            return (None, None)
        
        
        prev_uid = uids[i - 1] if i > 0 else None
        next_uid = uids[i + 1] if i < len(uids) - 1 else None
            
        if not self.uids_are_related(uid, prev_uid):
            prev_uid = None
        if not self.uids_are_related(uid, next_uid):
            next_uid = None
        return (prev_uid, next_uid)
        
    def uids_are_related(self, uid1, uid2):
        # We will perform a simple uid comparison
        # We could be more sophisticated! For example we could
        # inspect whether they belong to the same division
        if uid1 is None or uid2 is None:
            return False
        
        m1 = regex.match(r'\p{alpha}*(?:-\d+)?', uid1)[0]
        m2 = regex.match(r'\p{alpha}*(?:-\d+)?', uid2)[0]
        if m1 and m2 and m1 == m2:
            return True
    
    @staticmethod
    def get_text_author(filepath):
        """ Examines the file to discover the author
        
        This requires that a tag appears
        <meta author="Translated by Bhikkhu Bodhi">
        
        This must be in head and occur in the first 5 lines.
        The attribute must be quoted and should be fully qualified.
        <meta author='Edited by Bhante Sujato'>
        
        <meta author="Pali text from the Mahāsaṅgīti Tipiṭaka">
        
        """
        
        with filepath.open('r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i > 6:
                    break
                m = _Imm._author_search(line)
                if m:
                    return m[1]
        return None

    def _deep_md5(self, ids=False):
        """ Calculate a md5 for the data. Takes ~0.5s on a fast cpu.

        This will detect most inconsistencies in the contents of strings,
        ints, tuples, dicts and so on. As is always the case, carefully
        crafted different inputs could produce identical md5s, but this
        is highly unlikely to occur by chance.

        If ids is True, it additionally generates a md5 checksum on the
        id of every object encountered. The return value will be a tuple,
        (data_md5, id_md5). The data_md5 should be identical across
        different invocations of the program but the id_md5 will change.
        The id_md5 can detect some corruptions which the data_md5 won't,
        particularly when circular references are involved. For example
        data_md5 might not notice when the order of a list of parallels
        changes (if it has already seen each invidivudal parallel before),
        but id_md5 certainly will. On the other hand, at least in principle
        a change to an objects id need not invalidate the data - altough
        such things should not need to happen.
        
        """
        stack = []
        #md5 = hashlib.md5()
        #for b in atomicfy(self.collections, stack=stack):
            #md5.update(b)
        md5 = hashlib.md5(b"".join(atomicfy(self.collections, stack=stack)))
        if ids:
            md5ids = hashlib.md5(b"".join([str(id(a)).encode() for a in stack]))
            return (md5.hexdigest(), md5ids.hexdigest())
        return md5.hexdigest()

    def _check_md5(self, exception=None):
        new_md5 = self._deep_md5(ids=True)
        if not hasattr(self, 'imm_md5'):
            self.imm_md5 = new_md5
            logger.info('Generating md5 {}.'.format(new_md5))
        else:
            if self.imm_md5 == new_md5:
                logger.debug('md5s match')
            else:
                logger.error('md5 mismatch')
                if exception:
                    raise exception

def atomicfy(start, stack=None):
    """ Slice a unit into 'atomic' units (strs, bytes and ints)

    The individuals 'atoms' are yielded as bytes objects, suitable for
    consumption by a hashlib md5, sha or other function.

    If called with the stack attribute, stack must be a list. After the
    function as run, it will be populated with every object the function
    has seen. This has two purposes, first a stack of starting points
    can be entered, secondly you can perform further manupulations on the
    contents of the passed in stack.

    """

    if stack is None:
        stack = [start]
    elif start is not None and start not in stack:
        stack.append(start)
    touched = set()

    # Iterating over an object which is getting longer is fine in python.
    for obj in stack:
        oid = id(obj)
        try:
            if oid in touched:
                continue
            touched.add(oid)
        except TypeError:
            touched = set([oid])

        try:
            length = len(obj)
            # Object has length
            if length == 0:
                #For empty container, yield the type
                yield b't' + str(type(obj)).encode()
                continue
            
            try:
                yield obj.encode() # String?
                continue
            except AttributeError:
                try:
                    yield b'b' + obj # Bytes or btye-like?
                    continue
                except TypeError:
                    pass
            
            # Yield the length as an additional check
            yield b'l' + str(length).encode()
            
            try:
                for pair in obj.items(): # Dict-like?
                    stack.extend(pair)
                continue
            except AttributeError:
                pass

            try:
                stack.extend(obj) # List-like?
                continue
            except AttributeError:
                pass

        except TypeError:
            # Atomic (length-less) object.
            pass

        try:
            test = int(obj)
            yield b'n' + str(obj).encode()
            #intobj = abs(int(obj))
            #yield 'n' + intobj.tobytes(math.ceil(math.log(intobj+1, 2) / 8), 'big')
            continue
        except TypeError:
            pass

        # Yield the type. Useful for user classes.
        yield b't' + str(type(obj)).encode()

_imm = None
_updater = None

def imm():
    """ Get an instance of the DBR.

    Use only this function to get an instance of the DBR. For most intents
    and purposes the DBR should be considered a singleton. However it can
    be regenerated, and while being regenerated, a 'stale' copy can be be
    served, hence multiple versions can exist for a short time. (The stale
    copies will be garbage collected when they fall out of scope)
    
    If the imm is being generated, this function will block until it is
    ready. If the imm has already been generated, it is virtually free to
    call.

    """

    global _imm

    if not _imm:
        if _updater:
            _updater.ready.wait()
        else:
            _imm = _Imm(42)
    return _imm

def _mtime_recurse(path, timestamp=0):
    "Fast function for finding the latest mtime in a folder structure"

    timestamp = max(timestamp, path.stat().st_mtime_ns)
    for path1 in path.iterdir():
        if not path1.is_dir():
            continue
        timestamp = max(timestamp, _mtime_recurse(path1, timestamp))
    return timestamp
    
class Updater(threading.Thread):
    """ Ensures the imm is available and up to date.

    Checks the filesystem for changes which should be reflected
    in the imm.

    """
    
    
    ready = threading.Event() # Signal that the imm is ready.
    
    def get_change_timestamp(self):
        timestamp = str(sc.table_dir.stat().st_mtime_ns)

        if config.runtime_tests:
            timestamp += str(_mtime_recurse(sc.text_dir))
        else:
            # Detecting changes to git repository should be enough
            # for server environment.
            timestamp += str((sc.data_dir / '.git').stat().st_mtime_ns)
        return timestamp

    def run(self):
        global _imm
        # Give a few moments for the main thread to get started.
        time.sleep(1)
        while True:
            timestamp = self.get_change_timestamp()
            refresh_interval = config.db_refresh_interval
            
            # Check if imm is up to date
            if not _imm or _imm.timestamp != timestamp:
                logger.info('building imm')
                start = time.time();
                try:
                    _imm = _Imm(timestamp)
                    self.ready.set()
                    logger.info('imm build took {} seconds'.format(time.time() - start))
                    if config.runtime_tests:
                        # Do consistency checking.
                        _imm._check_md5()
                except Exception as e:
                    logger.error("Critical Error: DBR buid failed.", e)
                    # retry in case problem is fixed.
                    refresh_interval = min(20, refresh_interval)

            time.sleep(refresh_interval)

def start_updater():
    """Start the background updater."""

    global _updater
    if not _updater:
        _updater = Updater(name='imm_updater', daemon=True)
        _updater.start()
