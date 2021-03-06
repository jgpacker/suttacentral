import itertools as _itertools
import math as  _math
import regex as _regex
import unicodedata as _unicodedata

def numsortkey(input, index=0):
    """ Numerical sort. Handles identifiers well.

    Variable length ranges (i.e. 1.2 vs 1.11.111) are not handled gracefully.
    """
    if type(input) is str:
        string = input
    else:
        string = input[index]
        if string is None:
            return []
    return ( [int(a) if a.isnumeric() else a
                   for a in _regex.split(r'(\d+)', string)] )

def palisortkey(input, _charvalue = {}):
    """sorts strings into pali alphabetical order"""
    if len(_charvalue) == 0:
        charInorder = [
            '#', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'ā',
            'i', 'ī', 'u', 'ū', 'e', 'o', 'ṁ', 'ṃ', 'k', 'kh', 'g', 'gh', 'ṅ', 'c',
            'ch', 'j', 'jh', 'ñ', 'ṭ', 'ṭh', 'ḍ', 'ḍh', 'ṇ', 't', 'th', 'd',
            'dh', 'n', 'p', 'ph', 'b', 'bh', 'm', 'y', 'r', 'l', 'ḷ', 'v', 's', 'h',
        ]
        for i in range(0, len(charInorder)):
            c = charInorder[i]
            _charvalue[c] = i * 2
            if c != c.upper():
                _charvalue[c.upper()] = i * 2 - 1
        del charInorder
    mult = len(_charvalue)
    vals = []
    for i in range(0, len(input)):
        val = 0
        c1 = input[i]
        c2 = input[i:i+2]
        if c2 in _charvalue:
            val = _charvalue[c2]
            i += 1
        elif c1 in _charvalue:
            val = _charvalue[c1]
        vals.append(val)
    return tuple(vals)

def simplify_pali(string):
    rules = (
        (r'\P{alpha}', r''), #Non-alphabetical characters
        (r'nny', 'nn'), # nny (ññ) -> n
        (r'(.)(?=\1)', r''), #Remove duplicates
        (r'[mṁṃṅ](?=[gk])', r'n'), # 'n' before a 'g' or 'k'
        (r'by', 'vy'), # vy always, never by
    )

    out = string.casefold()
    for rule in rules:
        out = _regex.sub(rule[0], rule[1], out)
    out = _unicodedata.normalize('NFD', out)
    out = _regex.sub(r'\p{dia}', '', out)
    if len(out) > 5:
        out = _regex.sub(r'm\b', '', out) # Remove trailing m
    out = _regex.sub(r'(?<=[kgcjtdbp])h', r'', out) # Remove aspiration
    return out
    return ''

def simplify_english(string):
    rules = (
        (r'(.)(?=\1)', r''),
        (r'(?<=\w)[sc]', r'c'),
        (r'(?<=\w)[aou]+', r'a'),
        (r'(?<=\w)[ie]+', r'i'),
        (r'ia', 'ai'),
        )
    out = string
    for rule in rules:
        out = _regex.sub(rule[0], rule[1], out)
    return out

def simplify(string, langcode, default=None):
    if langcode == 'pi':
        return simplify_pali(string)
    elif langcode == 'en':
        return simplify_english(string)
    else:
        return default

def normalize(string):
    return _unicodedata.normalize('NFC', string)

def asciify_roman(string, _rexdia=_regex.compile(r'\p{dia}')):
    out = _unicodedata.normalize('NFD', string)
    out = _rexdia.sub('', out)
    out = out.replace('\xad', '')
    return out

def asciify(string, iso_code=None, _rexd=_regex.compile(r'\d+')):
    if iso_code in (None, 'pi', 'vn', 'de', 'fr'):
        return asciify_roman(string)
    if iso_code in ('zh'):
        return _rexd.sub('', codefy_chinese(string))
    return ''

_asc_tr = str.maketrans(
{
'ớ':'o','ȗ':'u','ở':'o','ồ':'o','ẍ':'x','ự':'u','ỗ':'o','ị':'i','ň':'n',
'ỏ':'o','ể':'e','ȳ':'y','ệ':'e','ń':'n','û':'u','ȇ':'e','ǹ':'n','ÿ':'y',
'ż':'z','ó':'o','ṙ':'r','ỷ':'y','’':"'",'ǵ':'g','ë':'e','ǩ':'k','≮':'<',
'ï':'i','ȕ':'u','ǭ':'o','ã':'a','ǡ':'a','ç':'c','ṯ':'t','ṝ':'r','ẓ':'z',
'ŭ':'u','ẗ':'t','ụ':'u','ẋ':'x','ẏ':'y','ž':'z','ẃ':'w','ẇ':'w','ĥ':'h',
'ẻ':'e','ȧ':'a','ế':'e','ļ':'l','ữ':'u','ẳ':'a','–':'-','ặ':'a','ẫ':'a',
'ắ':'a','ả':'a','ơ':'o','ầ':'a','ṛ':'r','ǘ':'u','ř':'r','ỳ':'y','ṟ':'r',
'ǜ':'u','ŝ':'s','ṓ':'o','ǐ':'i','ő':'o','ṗ':'p','ǔ':'u','ŕ':'r','ṋ':'n',
'ę':'e','ṏ':'o','ō':'o','ṃ':'m','ṇ':'n','ȟ':'h','ú':'u','ṻ':'u','ṿ':'v',
'ò':'o','ṳ':'u','ǰ':'j','ű':'u','ö':'o','ṷ':'u','ŵ':'w','ê':'e','ṫ':'t',
'ũ':'u','î':'i','≯':'>','ȓ':'r','â':'a','ṣ':'s','š':'s','ủ':'u','ṧ':'s',
'ť':'t','ḛ':'e','ȑ':'r','ḟ':'f','ĝ':'g','ḓ':'d','ẖ':'h','ḗ':'e','ĕ':'e',
'ȋ':'i','ĉ':'c','ȏ':'o','č':'c','ḃ':'b','ā':'a','ḇ':'b','ą':'a','ḻ':'l',
'ḿ':'m','ḋ':'d','ḳ':'k','ư':'u','ý':'y','ḷ':'l','ĵ':'j','ȫ':'o','ḉ':'c',
'ȯ':'o','ḅ':'b','ĭ':'i','ḣ':'h','ġ':'g','ḧ':'h','ḏ':'d','ộ':'o','ǟ':'a',
'ờ':'o','ț':'t','ố':'o','ổ':'o','ỵ':'y','ỉ':'i','ứ':'u','ȃ':'a','ề':'e',
'ņ':'n','ễ':'e','ź':'z','ǻ':'a','ḁ':'a',';':';','ừ':'u','ñ':'n','ḑ':'d',
'õ':'o','ǫ':'o','é':'e','`':'`','í':'i','≠':'=','á':'a','ǧ':'g','ș':'s',
'å':'a','‘':"'",'ẙ':'y','ẑ':'z','ử':'u','—':'-','ẕ':'z','ẉ':'w','ợ':'o',
'ỹ':'y','ẁ':'w','ẅ':'w','ĺ':'l','ẹ':'e','ľ':'l','ḍ':'d','ẽ':'e','ằ':'a',
'ẵ':'a','ẩ':'a','ậ':'a','ạ':'a','ấ':'a','ǚ':'u','ś':'s','ḱ':'k','ş':'s',
'ĩ':'i','ǒ':'o','ỡ':'o','ṑ':'o','ǖ':'u','ŗ':'r','ṕ':'p','ṽ':'v','ṉ':'n',
'ǎ':'a','ŏ':'o','ṍ':'o','ṁ':'m','ṅ':'n','ṹ':'u','“':'"','ü':'u','ḫ':'h',
'ų':'u','ṱ':'t','ŷ':'y','ô':'o','ṵ':'u','ū':'u','è':'e','ȩ':'e','ṥ':'s',
'ì':'i','ṭ':'t','ţ':'t','à':'a','ṡ':'s','ä':'a','ḯ':'i','ě':'e','ẘ':'w',
'ḙ':'e','ğ':'g','ů':'u','ḝ':'e','ē':'e','ȭ':'o','ė':'e','ḕ':'e','ċ':'c',
'ȉ':'i','ď':'d','ȍ':'o','ă':'a','ȁ':'a','ć':'c','ȅ':'e','ọ':'o','ḹ':'l',
'ḽ':'l','ù':'u','ȱ':'o','ķ':'k','ḵ':'k','ī':'i','ḩ':'h','į':'i','”':'"',
'ḭ':'i','ģ':'g','ḡ':'g','ṩ':'s','ḥ':'h'})

def strip_diacriticals(string):
    return string.translate(_asc_tr)
    

_rexnotascii = _regex.compile(r'\P{ascii}')
def codely(string):
    try:
        def subfn(m, code_map=_code_map):
            return code_map[m[0]]
        
        return _rexnotascii.sub(subfn, string).strip()
    except KeyError:
        return ''

def plainly(string):
    def subfn(m, plain_map=_plain_map):
        return plain_map.get(m[0], m[0])
    
    string = _rexnotascii.sub(subfn, string).strip()
    return asciify_roman(string)

_vel_to_uni_rules = (
    ('aa', 'ā'),
    ('ii', 'ī'),
    ('uu', 'ū'),
    ('.t', 'ṭ'),
    ('.d', 'ḍ'),
    ('~n', 'ñ'),
    ('.n', 'ṇ'),
    ('"n', 'ṅ'),
    ('.l', 'ḷ'),
    ('.m', 'ṃ'),
    ('.h', 'ḥ'),
    ('\'s', 'ś'),
    ('.s', 'ṣ'),
    ('.r', 'ṛ'),
    
    
    )

def vel_to_uni(string):
    for rule, repl in _vel_to_uni_rules:
        string = string.replace(rule, repl)
    return string

def uni_to_vel(string):
    for repl, rule in _vel_to_uni_rules:
        string = string.replace(rule, repl)

def _build_phonhashdata():
    # Generate Phonetic Hash Data
    start = (('A', 'AEIOU'),
            ('B', 'BFPVW'),
            ('C', 'CGJKQSXZ'),
            ('D', 'DT'),
            ('H', 'H'),
            ('R', 'RL'),
            ('M', 'MN'),
            ('Y', 'Y'))

    middle =(
            ('A', 'AEIOUYRL'),
            ('B', 'BFPVW'),
            ('C', 'CGJKQSXZH'),
            ('D', 'DT'),
            ('M', 'MN'))

    phonhashdata = ({}, [])
    for value, keys in start:
            phonhashdata[0].update((key, value) for key in keys)

    # Remove aspiration.
    phonhashdata[1].append((_regex.compile(r'(?<=[KGCJDT])H', _regex.I), ''))
    # Reduce consonant clusters
    phonhashdata[1].append((_regex.compile(r'[HYLRS]+(?![AEIOU])|(?<![^AEIOU])[HYLRS]+', _regex.I), ''))
    for value, keys in start:
        phonhashdata[1].append((_regex.compile(r'['+keys+r']+', _regex.I), value))
    
    return phonhashdata

_phonhashdata = _build_phonhashdata()
_syllabalize = _regex.compile(r'([^aiueoāīū\s]*)([aiueoāīū])((?!br|[kgcjdt]h)[^aiueoāīū\s](?=[^aiueoāīū\s]))?').findall

def phonhash(word, length=4):
    " Generate a phonetic hash for word "
    if not word:
        return word
    word = asciify(word)
    start = _phonhashdata[0].get(word[0].upper(), '')
    if len(word) == 1:
        return start
    rest = word
    for reg, repl in _phonhashdata[1]:
        rest = reg.sub(repl, rest, pos=1)
    if len(rest) == 1:
        return start
    if start == 'A' == rest[1]:
        return rest[1:1+length]
    else:
        return start + rest[1:length]

def _build_transform_cost():
    vowel_costs_table = {
        ('a', 'ā'): 10,
        ('i', 'ī'): 10,
        ('u', 'ū'): 10,
        ('a', 'e'): 30,
        ('a', 'o'): 30,
        ('i', 'e'): 25,
        ('u', 'o'): 25,
        }

    vowel_costs_map = {tuple(sorted(key)): value for key, value in vowel_costs_table.items()}

    # This is a Counter of all naturally occuring consonant clusters in the pali canon
    nat_cons = {'t', 's', 'n', 'ṃ', 'v', 'p', 'm', 'r', 'y', 'k', 'bh', 'd', 'h', 'ss', 'c', 'kkh', 'tt', 'g', 'nt', 'dh', 'l', 'kh', 'ṇ', 'mm', 'j', 'th', 'ññ', 'tth', 'bb', 'pp', 'ṭ', 'cc', 'ṭṭh', 'nn', 'yy', 'ñc', 'tv', 'cch', 'jj', 'ddh', 'gg', 'mp', 'kk', 'sm', 'b', 'nd', 'br', 'hm', 'ṃs', 'jjh', 'ṅk', 'ṃgh', 'ṅg', 'ṇḍ', 'dd', 'ṇṇ', 'ṭh', 'ṃv', 'ch', 'gh', 'll', 'ṅkh', 'mb', 'ph', 'by', 'ndh', 'mh', 'ḷ', 'ṇh', 'dv', 'ñj', 'bbh', 'mbh', 'tr', 'ñ', 'ñh', 'ṃy', 'jh', 'ndr', 'yh', 'sv', 'ḍḍh', 'ly', 'ḷh', 'ṭṭ', 'mph', 'ṃk', 'pph', 'vh', 'ṇṭh', 'ṃh', 'ky', 'nth', 'ṅgh', 'ntv', 'ggh', 'khv', 'nv', 'ṃkh', 'nh', 'ṃp', 'dr', 'ḍḍ', 'ṃd', 'ḍ', 'yv', 'gr', 'ṃm', 'ñch', 'ṃn', 'ty', 'ṇṭ', 'ṃg', 'gy', 'my', 'kl', 'ṅkhy', 'sn', 'ṃr', 'ṃj', 'ṃbh', 'kv', 'ṃdh', 'st', 'ñjh', 'ṃc', 'ṃnh', 'ṃt', 'pl', 'nty', 'ṃb', 'hv', 'ṃph', 'ṇy', 'sy', 'kr', 'ṃch', 'ṃsv', 'ṃsm', 'ṃl', 'ṃtv', 'ṃdv', 'hy', 'tthy', 'dm', 'ny', 'tn', 'ṅkhv', 'khy', 'ṃṭh', 'dhv', 'kkhy', 'pv', 'ḍh', 'ṃth'}

    transform_cost = dict()
    
    # Transform from double to single (20)
    for key in nat_cons:
        if len(key) > 1 and key[0] == key[1]:
            akey = asciify(key[1:])
            transform_cost[ tuple(sorted((asciify(key[1:]), key))) ] = 35 # Some will get replaced later.
            transform_cost[ tuple(sorted((key[1:], key))) ] = 20

    # Allow cheap transformations from ascii -> diacritical
    for key in nat_cons:
        akey = asciify(key)
        if akey != key:
            transform_cost[(akey, key)] = 10

    transform_cost.update( (tuple(sorted(key)), value) for key, value in vowel_costs_table.items() )

    # Self-transformation is free.
    transform_cost.update( {(key[0], key[0]) : 0 for key in transform_cost} )
    transform_cost.update( {(key, key) : 0 for key in nat_cons} )

    # Sanskrit -> Pali (cheap because they don't exist in pali)
    transform_cost[ ('mm', 'rm') ] = 5
    transform_cost[ ('bb', 'rv') ] = 5

    # Special cases
    transform_cost[ ('ṃ', 'ṅ') ] = 5
    transform_cost[ ('m', 'ṅ') ] = 5
    transform_cost[ ('c', 'j') ] = 20
    transform_cost[ ('b', 'p') ] = 30
    transform_cost[ ('by', 'vy') ] = 10

    for key in transform_cost:
        if tuple(sorted(key)) != key:
            print(key)
            raise
    return transform_cost
_transform_cost = _build_transform_cost()

def _trans_cost(cc1, cc2, _cache={}):
    "Cost of transforming one consonant cluster into another"
    if cc1 == cc2:
        return 0

    opair = pair = tuple(sorted( [cc1, cc2] ))
    try:
        return _cache[ pair ]
    except KeyError:
        pass

    cost = 0

    if pair[0][-1] != 'h' and pair[1][-1] == 'h':
        cost += 15
        pair = tuple(sorted( [pair[0], pair[1][:-1]] ))
    try:
        cost += transform_cost[pair]
    except KeyError:
        print(opair, end="  ")
        cost += 80
    _cache[opair] = cost
    return cost

_vowelsplitrex = _regex.compile(r'([aeiouāīū]+)').split
def mc4(word1, word2):
    pieces1 = _vowelsplitrex(word1.lower())
    pieces2 = _vowelsplitrex(word2.lower())
    pairs = [tuple(sorted(t)) for t in _itertools.zip_longest(pieces1, pieces2, fillvalue='')]
    cost = 0
    # Vowels

    for i, pair in enumerate(pairs):
        if pair[0] == pair[1]:
            continue
        if pair[0] == '' or pair[1] == '':
            cost += 800 / (5 + i)
        if i % 2 == 1:
            mod = 1
            if i <= len(pairs) - 1:
                mod = 0.66
            cost += _transform_cost.get(pair, 50) * mod
        else:
            try:
                cost += transform_cost[pair]
            except KeyError:
                try:
                    if pair[0][-1] != 'h' and pair[1][-1] == 'h':
                        cost += 15
                        pair = tuple(sorted((pair[0], pair[1][:-1])))
                except IndexError:
                    pass
                try:
                    cost += _transform_cost[pair]
                except KeyError:
                    if phonhash(pair[0]) == phonhash(pair[1]):
                        cost += 50
                    else:
                        cost += 80

    return cost

def mc4_boost(freq, factor=100):
    return _math.log(factor) / _math.log(factor + freq)

_unused = set(range(1, 31))
_unused.remove(1)
_unused = sorted(_unused)
_uni   = '–—‘’“”… '
_ascii = "".join(chr(_unused[i]) for i in range(1, 1+len(_uni)))

def mangle(string, _trans=str.maketrans(_uni, _ascii)):
    "Mangle unicode puncuation into unused ascii characters"
    return string.translate(_trans)

def demangle(string, _trans=str.maketrans(_ascii, _uni)):
    "Demangle unused ascii characters into unicode puncuation"
    out = string.translate(_trans)
    out = string[:36].replace('«br»', ' ')+string[36:]
    return out.replace('«br»', '<br>')

del _ascii, _uni, _unused

# This data was derived from sutta central.
_code_map={
"邠": "bin1 ", "次": "ci4 ", "麤": "cu1 ", "圓": "yuan2 ", "海": "hai3 ", "禮": "li3 ",
"侍": "shi4 ", "鬱": "yu4 ", "嚴": "yan2 ", "岸": "an4 ", "殺": "sha1 ", "固": "gu4 ",
"熾": "chi4 ", "持": "chi2 ", "垂": "chui2 ", "七": "qi1 ", "脅": "xie2 ", "疑": "yi2 ",
"有": "you3 ", "莊": "zhuang1 ", "憎": "zeng1 ", "災": "zai1 ", "梨": "li2 ", "徒": "tu2 ",
"五": "wu3 ", "讚": "zan4 ", "娛": "yu2 ", "攝": "she4 ", "歡": "huan1 ", "入": "ru4 ",
"橫": "heng2 ", "息": "xi1 ", "蟲": "chong2 ", "平": "ping2 ", "極": "ji2 ", "多": "duo1 ",
"避": "bi4 ", "十": "shi2 ", "雄": "xiong2 ", "鄙": "bi3 ", "賈": "jia3 ", "佉": "qu1 ",
"及": "ji2 ", "手": "shou3 ", "嫌": "xian2 ", "野": "ye3 ", "顏": "yan2 ", "卑": "bei1 ",
"習": "xi2 ", "著": "zhuo2 ", "牛": "niu2 ", "益": "yi4 ", "漢": "han4 ", "叵": "po3 ",
"冥": "ming2 ", "鴦": "yang1 ", "貧": "pin2 ", "義": "yi4 ", "劫": "jie2 ", "般": "ban1 ",
"奢": "she1 ", "央": "yang1 ", "露": "lu4 ", "尸": "shi1 ", "畏": "wei4 ", "施": "shi1 ",
"燃": "ran2 ", "退": "tui4 ", "漂": "piao1 ", "合": "he2 ", "邏": "luo2 ", "園": "yuan2 ",
"柔": "rou2 ", "鬚": "xu1 ", "力": "li4 ", "遠": "yuan3 ", "鏡": "jing4 ", "形": "xing2 ",
"廣": "guang3 ", "除": "chu2 ", "臥": "wo4 ", "給": "ji3 ", "糧": "liang2 ", "周": "zhou1 ",
"婬": "yin2 ", "灰": "hui1 ", "布": "bu4 ", "年": "nian2 ", "當": "dang1 ", "捺": "na4 ",
"髻": "ji4 ", "血": "xie3 ", "跡": "ji1 ", "黃": "huang2 ", "商": "shang1 ", "深": "shen1 ",
"回": "hui2 ", "半": "ban4 ", "請": "qing3 ", "闍": "she2 ", "烏": "wu1 ", "恐": "kong3 ",
"青": "qing1 ", "駕": "jia4 ", "魚": "yu2 ", "栴": "zhan1 ", "神": "shen2 ", "惟": "wei2 ",
"群": "qun2 ", "說": "shuo1 ", "墮": "duo4 ", "稱": "cheng1 ", "男": "nan2 ", "小": "xiao3 ",
"亂": "luan4 ", "會": "hui4 ", "者": "zhe3 ", "三": "san1 ", "名": "ming2 ", "意": "yi4 ",
"我": "wo3 ", "損": "sun3 ", "弓": "gong1 ", "耕": "geng1 ", "喘": "chuan3 ", "軟": "ruan3 ",
"增": "zeng1 ", "離": "li2 ", "罣": "gua4 ", "瓦": "wa3 ", "淨": "jing4 ", "癩": "lai4 ",
"孫": "sun1 ", "雲": "yun2 ", "塵": "chen2 ", "長": "zhang3 ", "鹹": "xian2 ", "死": "si3 ",
"波": "bo1 ", "命": "ming4 ", "西": "xi1 ", "觀": "guan1 ", "縛": "fu4 ", "哆": "duo1 ",
"蛇": "she2 ", "富": "fu4 ", "胎": "tai1 ", "返": "fan3 ", "恕": "shu4 ", "洲": "zhou1 ",
"鍛": "duan4 ", "汝": "ru3 ", "壞": "huai4 ", "慧": "hui4 ", "行": "xing2 ", "爪": "zhao3 ",
"嶷": "yi2 ", "第": "di4 ", "醯": "xi1 ", "焰": "yan4 ", "花": "hua1 ", "梵": "fan4 ",
"鐶": "huan2 ", "斷": "duan4 ", "刺": "ci4 ", "去": "qu4 ", "莫": "mo4 ", "酥": "su1 ",
"犁": "li2 ", "肅": "su4 ", "文": "wen2 ", "檀": "tan2 ", "舊": "jiu4 ", "王": "wang2 ",
"饒": "rao4 ", "福": "fu2 ", "磨": "mo2 ", "賓": "bin1 ", "演": "yan3 ", "搖": "yao2 ",
"甘": "gan1 ", "稚": "zhi4 ", "貝": "bei4 ", "頞": "e4 ", "祠": "ci2 ", "幢": "chuang2 ",
"潤": "run4 ", "譬": "pi4 ", "娑": "suo1 ", "遮": "zhe1 ", "六": "liu4 ", "干": "gan1 ",
"翳": "yi4 ", "學": "xue2 ", "數": "shu4 ", "空": "kong1 ", "荼": "tu2 ", "祀": "si4 ",
"時": "shi2 ", "心": "xin1 ", "順": "shun4 ", "豆": "dou4 ", "闇": "an4 ", "犍": "jian1 ",
"散": "san4 ", "歌": "ge1 ", "過": "guo4 ", "量": "liang4 ", "穢": "hui4 ", "染": "ran3 ",
"仙": "xian1 ", "驚": "jing1 ", "毛": "mao2 ", "卜": "bu3 ", "上": "shang4 ", "類": "lei4 ",
"無": "wu2 ", "律": "lyu4 ", "鬥": "dou4 ", "昧": "mei4 ", "隨": "sui2 ", "崩": "beng1 ",
"禪": "chan2 ", "倫": "lun2 ", "失": "shi1 ", "網": "wang3 ", "縷": "lyu3 ", "洹": "huan2 ",
"覺": "jue2 ", "頻": "pin2 ", "缽": "bo1 ", "犀": "xi1 ", "慈": "ci2 ", "來": "lai2 ",
"膊": "fu3 ", "訟": "song4 ", "章": "zhang1 ", "巢": "chao2 ", "夫": "fu1 ", "賤": "jian4 ",
"步": "bu4 ", "迦": "jia1 ", "雨": "yu3 ", "自": "zi4 ", "火": "huo3 ", "蘭": "lan2 ",
"已": "yi3 ", "味": "wei4 ", "賴": "lai4 ", "獵": "lie4 ", "相": "xiang4 ", "出": "chu1 ",
"罽": "ji4 ", "現": "xian4 ", "真": "zhen1 ", "獅": "shi1 ", "就": "jiu4 ", "狐": "hu2 ",
"擔": "dan4 ", "捕": "bu3 ", "轉": "zhuan3 ", "默": "mo4 ", "教": "jiao4 ", "衛": "wei4 ",
"補": "bu3 ", "牟": "mou2 ", "索": "suo3 ", "座": "zuo4 ", "薩": "sa4 ", "優": "you1 ",
"鞭": "bian1 ", "戰": "zhan4 ", "熱": "re4 ", "甲": "jia3 ", "口": "kou3 ", "水": "shui3 ",
"丸": "wan2 ", "方": "fang1 ", "鳥": "niao3 ", "言": "yan2 ", "要": "yao4 ", "各": "ge4 ",
"先": "xian1 ", "丈": "zhang4 ", "養": "yang3 ", "泉": "quan2 ", "龍": "long2 ", "成": "cheng2 ",
"貓": "mao1 ", "算": "suan4 ", "帝": "di4 ", "丘": "qiu1 ", "愚": "yu2 ", "猿": "yuan2 ",
"功": "gong1 ", "賣": "mai4 ", "句": "ju4 ", "盧": "lu2 ", "器": "qi4 ", "士": "shi4 ",
"端": "duan1 ", "堅": "jian1 ", "揵": "qian2 ", "雷": "lei2 ", "善": "shan4 ", "祺": "qi2 ",
"塼": "zhuan1 ", "所": "suo3 ", "私": "si1 ", "終": "zhong1 ", "剛": "gang1 ", "鑄": "zhu4 ",
"曇": "tan2 ", "盜": "dao4 ", "灌": "guan4 ", "忍": "ren3 ", "金": "jin1 ", "石": "shi2 ",
"杖": "zhang4 ", "乘": "cheng2 ", "慚": "can2 ", "別": "bie2 ", "度": "du4 ", "澡": "zao3 ",
"御": "yu4 ", "邪": "xie2 ", "脫": "tuo1 ", "馬": "ma3 ", "中": "zhong1 ", "窮": "qiong2 ",
"兒": "er2 ", "報": "bao4 ", "申": "shen1 ", "強": "qiang2 ", "吹": "chui1 ", "為": "wei2 ",
"伏": "fu2 ", "匿": "ni4 ", "老": "lao3 ", "薄": "bo2 ", "舅": "jiu4 ", "皆": "jie1 ",
"少": "shao3 ", "邊": "bian1 ", "不": "bu4 ", "能": "neng2 ", "怨": "yuan4 ", "粒": "li4 ",
"弗": "fu2 ", "婦": "fu4 ", "愛": "ai4 ", "未": "wei4 ", "珠": "zhu1 ", "起": "qi3 ",
"嚫": "chen4 ", "渝": "yu2 ", "摩": "mo2 ", "八": "ba1 ", "陂": "po1 ", "髮": "fa4 ",
"魯": "lu3 ", "痴": "chi1 ", "延": "yan2 ", "白": "bai2 ", "毀": "hui3 ", "集": "ji2 ",
"均": "jun1 ", "葉": "she4 ", "態": "tai4 ", "降": "xiang2 ", "筏": "fa2 ", "提": "ti2 ",
"灑": "sa3 ", "他": "ta1 ", "土": "tu3 ", "釜": "fu3 ", "晝": "zhou4 ", "閣": "ge2 ",
"瘦": "shou4 ", "木": "mu4 ", "坌": "ben4 ", "醫": "yi1 ", "賢": "xian2 ", "種": "zhong3 ",
"邱": "qiu1 ", "足": "zu2 ", "德": "de2 ", "輸": "shu1 ", "油": "you2 ", "嗏": "cha1 ",
"戾": "li4 ", "殿": "dian4 ", "結": "jie2 ", "銅": "tong2 ", "蘆": "lu2 ", "逆": "ni4 ",
"月": "yue4 ", "見": "jian4 ", "邑": "yi4 ", "吒": "zha4 ", "經": "jing1 ", "純": "chun2 ",
"世": "shi4 ", "林": "lin2 ", "魔": "mo2 ", "夜": "ye4 ", "頂": "ding3 ", "占": "zhan1 ",
"惡": "e4 ", "屢": "lyu3 ", "緣": "yuan2 ", "若": "ruo4 ", "哩": "li3 ", "沒": "mo4 ",
"華": "hua2 ", "印": "yin4 ", "惱": "nao3 ", "執": "zhi2 ", "移": "yi2 ", "郁": "yu4 ",
"求": "qiu2 ", "旃": "zhan1 ", "彈": "tan2 ", "靜": "jing4 ", "遊": "you2 ", "釋": "shi4 ",
"剎": "cha4 ", "子": "zi3 ", "女": "nyu3 ", "聞": "wen2 ", "湖": "hu2 ", "安": "an1 ",
"練": "lian4 ", "恚": "hui4 ", "兜": "dou1 ", "伊": "yi1 ", "察": "cha2 ", "負": "fu4 ",
"客": "ke4 ", "性": "xing4 ", "風": "feng1 ", "師": "shi1 ", "嶮": "xian3 ", "蜱": "pi2 ",
"主": "zhu3 ", "疾": "ji2 ", "尿": "niao4 ", "漁": "yu2 ", "覆": "fu4 ", "嬉": "xi1 ",
"羊": "yang2 ", "下": "xia4 ", "二": "er4 ", "氏": "shi4 ", "休": "xiu1 ", "樓": "lou2 ",
"首": "shou3 ", "頗": "po1 ", "傘": "san3 ", "錙": "zi1 ", "減": "jian3 ", "障": "zhang4 ",
"親": "qin1 ", "睡": "shui4 ", "詣": "yi4 ", "略": "lue4 ", "顧": "gu4 ", "部": "bu4 ",
"道": "dao4 ", "繫": "xi4 ", "業": "ye4 ", "差": "cha1 ", "影": "ying3 ", "篲": "hui4 ",
"宿": "su4 ", "偷": "tou1 ", "裸": "luo3 ", "曼": "man4 ", "好": "hao3 ", "寂": "ji4 ",
"驃": "biao1 ", "故": "gu4 ", "等": "deng3 ", "之": "zhi1 ", "疲": "pi2 ", "毒": "du2 ",
"拔": "ba2 ", "虛": "xu1 ", "雜": "za2 ", "喻": "yu4 ", "瑟": "se4 ", "池": "chi2 ",
"耨": "nou4 ", "輪": "lun2 ", "溫": "wen1 ", "積": "ji1 ", "欲": "yu4 ", "難": "nan2 ",
"然": "ran2 ", "傷": "shang1 ", "逸": "yi4 ", "放": "fang4 ", "日": "ri4 ", "茂": "mao4 ",
"毗": "pi2 ", "涅": "nie4 ", "須": "xu1 ", "玉": "yu4 ", "弊": "bi4 ", "事": "shi4 ",
"憍": "jiao1 ", "伽": "qie2 ", "誓": "shi4 ", "外": "wai4 ", "際": "ji4 ", "屠": "tu2 ",
"信": "xin4 ", "止": "zhi3 ", "鉤": "gou1 ", "藥": "yao4 ", "僧": "seng1 ", "菩": "pu2 ",
"罪": "zui4 ", "字": "zi4 ", "燭": "zhu2 ", "浮": "fu2 ", "柱": "zhu4 ", "歲": "sui4 ",
"其": "qi2 ", "睺": "hou4 ", "衰": "shuai1 ", "病": "bing4 ", "俱": "ju4 ", "偈": "jie2 ",
"叉": "cha1 ", "與": "yu3 ", "槍": "qiang1 ", "九": "jiu3 ", "近": "jin4 ", "藕": "ou3 ",
"願": "yuan4 ", "四": "si4 ", "聚": "ju4 ", "瘡": "chuang1 ", "室": "shi4 ", "愧": "kui4 ",
"利": "li4 ", "斯": "si1 ", "末": "mo4 ", "頭": "tou2 ", "支": "zhi1 ", "新": "xin1 ",
"趣": "qu4 ", "鐵": "tie3 ", "夷": "yi2 ", "樹": "shu4 ", "人": "ren2 ", "鼻": "bi2 ",
"鴿": "ge1 ", "門": "men2 ", "瞋": "chen1 ", "肆": "si4 ", "舉": "ju3 ", "國": "guo2 ",
"後": "hou4 ", "在": "zai4 ", "窒": "chi4 ", "果": "guo3 ", "思": "si1 ", "生": "sheng1 ",
"晡": "bu1 ", "勢": "shi4 ", "正": "zheng4 ", "古": "gu3 ", "內": "nei4 ", "物": "wu4 ",
"雪": "xue3 ", "恭": "gong1 ", "蓮": "lian2 ", "即": "ji2 ", "菴": "an1 ", "呵": "a1 ",
"具": "ju4 ", "觸": "chu4 ", "特": "te4 ", "建": "jian4 ", "杻": "chou3 ", "聽": "ting1 ",
"繁": "fan2 ", "千": "qian1 ", "便": "bian4 ", "居": "ju1 ", "祇": "qi2 ", "燈": "deng1 ",
"車": "che1 ", "齋": "zhai1 ", "矌": "guang4 ", "苦": "ku3 ", "問": "wen4 ", "比": "bi3 ",
"廚": "chu2 ", "佛": "fo2 ", "糞": "fen4 ", "素": "su4 ", "因": "yin1 ", "立": "li4 ",
"訶": "he1 ", "本": "ben3 ", "炭": "tan4 ", "藍": "lan2 ", "田": "tian2 ", "戲": "xi4 ",
"害": "hai4 ", "猴": "hou2 ", "耶": "ye1 ", "誹": "fei3 ", "瞻": "zhan1 ", "眼": "yan3 ",
"樂": "le4 ", "掃": "sao3 ", "耆": "qi2 ", "蘊": "yun4 ", "例": "li4 ", "后": "hou4 ",
"紐": "niu3 ", "云": "yun2 ", "戒": "jie4 ", "怖": "bu4 ", "鸚": "ying1 ", "供": "gong4 ",
"蜜": "mi4 ", "盡": "jin4 ", "牢": "lao2 ", "遫": "su4 ", "孤": "gu1 ", "泥": "ni2 ",
"釧": "chuan4 ", "郭": "guo1 ", "異": "yi4 ", "色": "se4 ", "典": "dian3 ", "竹": "zhu2 ",
"智": "zhi4 ", "蟻": "yi3 ", "彼": "bi3 ", "壽": "shou4 ", "謗": "bang4 ", "盛": "sheng4 ",
"獄": "yu4 ", "奈": "nai4 ", "嫉": "ji2 ", "彌": "mi2 ", "豎": "shu4 ", "族": "zu2 ",
"嵐": "lan2 ", "黑": "hei1 ", "孔": "kong3 ", "法": "fa3 ", "聖": "sheng4 ", "肉": "rou4 ",
"食": "shi2 ", "作": "zuo4 ", "鍵": "jian4 ", "連": "lian2 ", "鹽": "yan2 ", "骨": "gu3 ",
"天": "tian1 ", "薪": "xin1 ", "含": "han2 ", "責": "ze2 ", "是": "shi4 ", "諸": "zhu1 ",
"耳": "er3 ", "岳": "yue4 ", "家": "jia1 ", "澤": "ze2 ", "阿": "a4 ", "憂": "you1 ",
"切": "qie4 ", "越": "yue4 ", "大": "da4 ", "和": "he2 ", "倒": "dao3 ", "縏": "pan2 ",
"間": "jian1 ", "輕": "qing1 ", "折": "zhe2 ", "礙": "ai4 ", "鞞": "bi4 ", "曠": "kuang4 ",
"鵡": "wu3 ", "恣": "zi4 ", "壤": "rang3 ", "實": "shi2 ", "牧": "mu4 ", "煩": "fan2 ",
"藪": "sou3 ", "得": "de2 ", "修": "xiu1 ", "杵": "chu3 ", "寶": "bao3 ", "沙": "sha1 ",
"鋸": "ju1 ", "重": "zhong4 ", "鹿": "lu4 ", "雀": "que4 ", "流": "liu2 ", "棄": "qi4 ",
"密": "mi4 ", "光": "guang1 ", "緊": "jin3 ", "迎": "ying2 ", "燒": "shao1 ", "桓": "huan2 ",
"何": "he2 ", "取": "qu3 ", "饉": "jin3 ", "拘": "ju1 ", "淚": "lei4 ", "瓜": "gua1 ",
"陟": "zhi4 ", "閡": "he2 ", "夢": "meng4 ", "患": "huan4 ", "沫": "mo4 ", "箭": "jian4 ",
"踰": "yu2 ", "釣": "diao4 ", "破": "po4 ", "城": "cheng2 ", "船": "chuan2 ", "治": "zhi4 ",
"尼": "ni2 ", "眾": "zhong4 ", "一": "yi1 ", "羅": "luo2 ", "計": "ji4 ", "醉": "zui4 ",
"同": "tong2 ", "角": "jiao3 ", "序": "xu4 ", "閑": "xian2 ", "如": "ru2 ", "枕": "zhen3 ",
"化": "hua4 ", "記": "ji4 ", "香": "xiang1 ", "甚": "shen4 ", "闡": "chan3 ", "慢": "man4 ",
"淫": "yin2 ", "知": "zhi1 ", "獦": "ge2 ", "鉗": "qian2 ", "豬": "zhu1 ", "揭": "jie1 ",
"滯": "zhi4 ", "陰": "yin1 ", "己": "ji3 ", "想": "xiang3 ", "念": "nian4 ", "留": "liu2 ",
"絺": "chi1 ", "可": "ke3 ", "松": "song1 ", "滿": "man3 ", "陀": "tuo2 ", "勇": "yong3 ",
"應": "ying4 ", "蓋": "gai4 ", "母": "mu3 ", "低": "di1 ", "驢": "lyu2 ", "酒": "jiu3 ",
"達": "da2 ", "濕": "shi1 ", "蹟": "ji4 ", "非": "fei1 ", "廟": "miao4 ", "技": "ji4 ",
"乳": "ru3 ", "春": "chun1 ", "誦": "song4 ", "貪": "tan1 ", "爭": "zheng1 ", "皮": "pi2 ",
"萍": "ping2 ", "獸": "shou4 ", "悲": "bei1 ", "那": "na4 ", "壹": "yi1 ", "根": "gen1 ",
"夏": "xia4 ", "於": "yu2 ", "往": "wang3 ", "封": "feng1 ", "清": "qing1 ", "指": "zhi3 ",
"守": "shou3 ", "舍": "she4 ", "漏": "lou4 ", "向": "xiang4 ", "鼓": "gu3 ", "百": "bai3 ",
"猗": "yi1 ", "掘": "jue2 ", "雞": "ji1 ", "崛": "jue2 ", "喜": "xi3 ", "初": "chu1 ",
"弟": "di4 ", "象": "xiang4 ", "飢": "ji1 ", "諦": "di4 ", "況": "kuang4 ", "旬": "xun2 ",
"目": "mu4 ", "厭": "yan4 ", "山": "shan1 ", "慳": "qian1 ", "致": "zhi4 ", "陵": "ling2 ",
"護": "hu4 ", "塞": "sai4 ", "穽": "jing3 ", "曾": "ceng2 ", "使": "shi3 ", "陳": "chen2 ",
"龜": "gui1 ", "賊": "zei2 ", "此": "ci3 ", "前": "qian2 ", "黎": "li2 ", "住": "zhu4 ",
"惒": "he2 ", "河": "he2 ", "身": "shen1 ", "處": "chu4 ", "論": "lun4 ", "南": "nan2 ",
"毘": "pi2 ", "琴": "qin2 ", "罵": "ma4 ", "關": "guan1 ", "點": "dian3 ", "眠": "mian2 ",
"財": "cai2 ", "構": "gou4 ", "麥": "mai4 ", "癡": "chi1 ", "開": "kai1 ", "枯": "ku1 ",
"地": "di4 ", "常": "chang2 ", "衣": "yi1 ", "父": "fu4 ", "玷": "dian4 ", "寤": "wu4 ",
"閻": "yan2 ", "瞿": "qu1 ", "最": "zui4 ", "節": "jie2 ", "堂": "tang2 ", "億": "yi4 ",
"分": "fen1 ", "率": "shuai4 ", "嬈": "rao2 ", "吼": "hou3 ", "尊": "zun1 ", "照": "zhao4 ",
"劍": "jian4 ", "明": "ming2 ", "怒": "nu4 ", "繩": "sheng2 ", "鬘": "man2 ", "調": "diao4 ",
"動": "dong4 ", "泡": "pao4 ", "衢": "qu2 ", "解": "jie3 ", "以": "yi3 ", "試": "shi4 ",
"禁": "jin4 ", "獨": "du2 ", "志": "zhi4 ", "敬": "jing4 ", "竭": "jie2 ", "普": "pu3 ",
"聲": "sheng1 ", "至": "zhi4 ", "奴": "nu2 ", "究": "jiu1 ", "歸": "gui1 ", "惹": "re3 ",
"塚": "zhong3 ", "乾": "gan1 ", "忿": "fen4 ", "品": "pin3 ", "槃": "pan2 ", "滅": "mie4 ",
"婆": "po2 ", "跋": "ba2 ", "界": "jie4 ", "諍": "zheng1 ", "坐": "zuo4 ", "恒": "heng2 ",
"姓": "xing4 ", "捨": "she3 ", "乞": "qi3 ", "受": "shou4 ", "識": "shi4 ", "痛": "tong4 ",
"勝": "sheng4 ", "繞": "rao4 ", "濟": "ji4",
"兔": "tou3", "縈": "jin4", "餅": "beng2", "淳": "seon4", "獲": "wok6",
}


_plain_map = {k: _regex.sub(r'\d', '', v) for k, v in _code_map.items()}
_plain_map.update({'–': '-', '—': '-', '−': '-', '\xad':''})

_code_map.update((t[1], t[0]) for t in _vel_to_uni_rules)
_code_map.update({'–': '-', '—': '--', '−': '-', '\xad':''})
