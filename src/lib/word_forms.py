"""Does an example sentence use the word? (spec 021, research R4)

contains_form() accepts the word itself or its natural inflections:
regular endings (-s, -es, -ed, -d, -ing, -er, -est, y→ies/ied, dropped
final e, doubled final consonant) and the forms of common irregular verbs.
A phrase matches word by word, in order, with its first word inflected
and gaps of at most two words, so "give up" matches "gave it up"."""

import re

# Reviewed: base form → past and past participle forms (and other common
# forms), for the irregular verbs a learner meets most.
_IRREGULAR = """
arise arose arisen | awake awoke awoken | be was were been is am are | bear bore born borne |
beat beat beaten | become became become | begin began begun | bend bent bent | bet bet bet |
bid bid bid | bind bound bound | bite bit bitten | bleed bled bled | blow blew blown |
break broke broken | breed bred bred | bring brought brought | broadcast broadcast broadcast |
build built built | burn burnt burnt burned | burst burst burst | buy bought bought |
cast cast cast | catch caught caught | choose chose chosen | cling clung clung | come came come |
cost cost cost | creep crept crept | cut cut cut | deal dealt dealt | dig dug dug | do did done does |
draw drew drawn | dream dreamt dreamt dreamed | drink drank drunk | drive drove driven |
eat ate eaten | fall fell fallen | feed fed fed | feel felt felt | fight fought fought |
find found found | flee fled fled | fling flung flung | fly flew flown flies | forbid forbade forbidden |
forecast forecast forecast | forget forgot forgotten | forgive forgave forgiven | freeze froze frozen |
get got gotten | give gave given | go went gone goes | grind ground ground | grow grew grown |
hang hung hung | have had had has | hear heard heard | hide hid hidden | hit hit hit |
hold held held | hurt hurt hurt | keep kept kept | kneel knelt knelt | know knew known |
lay laid laid | lead led led | lean leant leant leaned | leap leapt leapt | learn learnt learnt learned |
leave left left | lend lent lent | let let let | lie lay lain lying | light lit lit lighted |
lose lost lost | make made made | mean meant meant | meet met met | mislead misled misled |
mistake mistook mistaken | overcome overcame overcome | overtake overtook overtaken |
pay paid paid | prove proved proven | put put put | quit quit quit | read read read |
rid rid rid | ride rode ridden | ring rang rung | rise rose risen | run ran run |
say said said | see saw seen | seek sought sought | sell sold sold | send sent sent |
set set set | sew sewed sewn | shake shook shaken | shed shed shed | shine shone shone |
shoot shot shot | show showed shown | shrink shrank shrunk | shut shut shut | sing sang sung |
sink sank sunk | sit sat sat | sleep slept slept | slide slid slid | sling slung slung |
smell smelt smelt smelled | sow sowed sown | speak spoke spoken | speed sped sped |
spell spelt spelt spelled | spend spent spent | spill spilt spilt spilled | spin spun spun |
spit spat spat | split split split | spoil spoilt spoilt spoiled | spread spread spread |
spring sprang sprung | stand stood stood | steal stole stolen | stick stuck stuck |
sting stung stung | stink stank stunk | strike struck struck | strive strove striven |
swear swore sworn | sweep swept swept | swell swelled swollen | swim swam swum |
swing swung swung | take took taken | teach taught taught | tear tore torn | tell told told |
think thought thought | throw threw thrown | thrust thrust thrust | tread trod trodden |
undergo underwent undergone | understand understood understood | undertake undertook undertaken |
undo undid undone | upset upset upset | wake woke woken | wear wore worn | weave wove woven |
weep wept wept | win won won | wind wound wound | withdraw withdrew withdrawn |
withhold withheld withheld | withstand withstood withstood | wring wrung wrung | write wrote written |
foresee foresaw foreseen | outdo outdid outdone | rewrite rewrote rewritten | retell retold retold |
uphold upheld upheld | overhear overheard overheard | oversee oversaw overseen
"""

IRREGULAR_VERBS: dict[str, set[str]] = {}
for _entry in _IRREGULAR.split("|"):
    _forms = _entry.split()
    if _forms:
        IRREGULAR_VERBS[_forms[0]] = set(_forms[1:])

_VOWELS = set("aeiou")
_TOKEN = re.compile(r"[a-z]+(?:'[a-z]+)?")


def inflections(word: str) -> set[str]:
    """The word and its regular and irregular inflected forms."""
    w = word.lower()
    forms = {w, w + "s", w + "es", w + "ed", w + "d", w + "ing", w + "er", w + "est"}
    if w.endswith("y") and len(w) > 2 and w[-2] not in _VOWELS:
        forms |= {w[:-1] + "ies", w[:-1] + "ied", w[:-1] + "ier", w[:-1] + "iest"}
    if w.endswith("e"):
        forms |= {w[:-1] + "ing", w[:-1] + "ed"}
    if len(w) >= 3 and w[-1] not in _VOWELS | {"w", "x", "y"} and w[-2] in _VOWELS and w[-3] not in _VOWELS:
        forms |= {w + w[-1] + "ed", w + w[-1] + "ing", w + w[-1] + "er"}
    if w.endswith("ie"):
        forms.add(w[:-2] + "ying")
    forms |= IRREGULAR_VERBS.get(w, set())
    return forms


def _tokens(text: str) -> list[str]:
    # "I'm" → "i", "m"-free tokens: split contractions off the word.
    return [t.split("'")[0] for t in _TOKEN.findall(text.lower())]


def contains_form(sentence: str, english: str) -> bool:
    """True when *sentence* uses *english* (a word or phrase) naturally."""
    words = _tokens(english)
    tokens = _tokens(sentence)
    if not words or not tokens:
        return False
    first = inflections(words[0])
    rest = words[1:]
    for start, token in enumerate(tokens):
        if token not in first:
            continue
        position = start
        for word in rest:
            window = tokens[position + 1 : position + 4]  # gap of at most 2 words
            if word not in window:
                break
            position += 1 + window.index(word)
        else:
            return True
    return False
