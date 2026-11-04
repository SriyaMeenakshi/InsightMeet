"""Linguistic cue patterns shared by the classifier rule layer and extractors.

All patterns are plain regular expressions so every decision is explainable.
"""
import re

I = re.IGNORECASE
_A = "['’]"  # apostrophe variants

# ------------------------------------------------------------------ hedges
HEDGE_RE = re.compile(
    r"\b(maybe|perhaps|possibly|probably|might|hopefully|i guess|i think|not sure|"
    r"if (?:i|we|there|time|possible)|tentatively|depending|kind of|sort of|"
    rf"i{_A}ll try|i can try|try to|should be able to|could be|may be)\b", I)

QUESTION_START_RE = re.compile(
    r"^(?:so |and |but |okay,? |ok,? )?(who|what|when|where|why|how|which|is|are|was|were|do|does|did|"
    r"can|could|will|would|should|shall|have|has|any)\b", I)

# suggestion-shaped questions are SUGGESTION, not QUESTION
SUGGESTION_RE = re.compile(
    r"\b(what if|how about|what about|why don[’']?t we|why not|we could|we might|could we|"
    r"should we|shall we|i suggest|i propose|i[’']d suggest|i would suggest|suggest(?:ion)?|"
    r"my suggestion|an idea|one idea|one option|another option|alternatively|it might be better|"
    r"would it be better|we can try|we can also|let[’']?s consider|worth (?:trying|considering|exploring)|"
    r"i think we should|we should consider|might be worth|maybe we|maybe use|perhaps we|"
    r"perhaps use|maybe i|how would you feel|may be better|would be better|"
    r"why don[’']?t you|thoughts on|any thoughts|what do you think about|how do you feel about|opinions on|maybe|perhaps)\b", I)

# an explicit, unhedged decision statement
DECISION_RE = re.compile(
    r"\b(we(?:[’']ve| have)? (?:decided|agreed|concluded|resolved)|"
    r"(?:it[’']s|it is|that[’']s|that is) (?:been )?(?:decided|settled|final|confirmed)|decision made|let[’']?s not (?:switch|use|go|do|move|change|drop|add)|"
    r"(?:the )?final (?:decision|call|choice)|decision (?:is|was)|"
    r"(?:let[’']?s|let us) (?:go with|use|stick (?:with|to)|move (?:forward )?with|keep|switch to|choose|pick|adopt|drop|skip|postpone|delay|push|move|reschedule)|"
    r"we(?:[’']ll| will|[’']re going to| are going to) (?:go with|use|stick (?:with|to)|move (?:forward )?with|switch to|adopt|keep|drop|skip|postpone|choose|pick)|"
    r"we(?:[’']ll| will) (?:move|push|reschedule|postpone)|"
    r"(?:we[’']re|we are) (?:going with|sticking with|moving to|switching to)|"
    r"going with|sticking with|settled on|we chose|we(?:[’']ve| have) chosen|the plan is to|"
    r"approved|agreed(?: to| on| that|,)|decided (?:to|on|that)|that[’']s the plan|it[’']s a deal|"
    r"(?:is|are) (?:now )?(?:the )?(?:official|final|confirmed))\b", I)

_LEAD = r"(?:(?:hmm+|well|uh+|um+|honestly|actually|so|ok|okay|yeah|i mean)[,.]?\s+)*"
AFFIRM_RE = re.compile(
    r"^" + _LEAD + r"(?:(?:yes|yeah|yep|yup|sure|okay|ok|alright|right|agreed|fine|absolutely|definitely|great|good|perfect|cool)\b[,.! ]*)+"
    r"|^(?:sounds? (?:good|great|fine|like a plan)|works for me|good (?:idea|call|point)|"
    r"let[’']?s do (?:that|it|this)|let[’']?s go (?:with that|for it)|go for it|do it|i agree|i[’']m (?:fine|good|okay) with|"
    r"makes sense|that works|i like (?:it|that)|i[’']m in|fair enough|deal|go ahead|approved)\b", I)

REJECT_RE = re.compile(
    rf"^{_LEAD}(?:no\b|nope\b|nah\b|i (?:don[’']?t|do not) (?:think|like|agree)|i disagree|not (?:a good idea|sure\b|really|convinced)|"
    rf"let[’']?s not|(?:that|it) (?:won[’']?t|will not|wouldn[’']?t|doesn[’']?t|is not|isn[’']?t) (?:work|be)|"
    rf"i[’']?d rather not|too (?:costly|expensive|risky|complex|slow)|hard pass|"
    rf"(?:i[’']?m )?(?:not )?against (?:it|that|this)|rather not|bad idea)", I)

# -------------------------------------------------------------- commitments
SELF_TENTATIVE = (rf"(?:i can try(?: to)?|i{_A}ll try(?: to)?|i{_A}ll probably|i will probably|probably i{_A}ll|"
                  rf"i think i can|i guess i can|hopefully i(?:{_A}ll| will| can)?|i might|i may|i could|i should|"
                  rf"i can(?!{_A}?t\b|not\b))")
SELF_DEFINITE = (rf"(?:i{_A}ll|i will|i shall|i{_A}m going to|i am going to|i{_A}m gonna|let me|"
                 rf"i{_A}m (?:taking|handling|doing|on)|i am (?:taking|handling|doing)|i take|i got|i{_A}ve got|"
                 rf"i{_A}ll go ahead and)")
SELF_OBLIG = rf"(?:i need to|i have to|i must|i gotta|i{_A}ve got to|i{_A}m supposed to)"
SELF_NEG = re.compile(rf"\b(?:won{_A}t|can{_A}t|cannot|don{_A}t|not going to|isn{_A}t going to|unable to|"
                      rf"couldn{_A}t|wouldn{_A}t)\b", I)

GROUP_SUBJ = r"(?:we|someone|somebody|everyone|everybody|the team|team|whoever|one of us|nobody)"
MODAL_THIRD = (rf"(?:will|{_A}ll|is going to|are going to|is gonna|needs? to|has to|have to|must|should|can|could|might|may|"
               rf"is responsible for|are responsible for|will be responsible for|is handling|are handling|is taking|"
               rf"is working on|is in charge of|will take|takes|owns|is doing|will handle|will own)")
TENTATIVE_THIRD = re.compile(r"^(?:can|could|might|may|should)$", I)

WORK_VERB_HINT = re.compile(
    r"^(?:pair|meet|sync|coordinate|help|support|join|debug|sort|tackle|resolve|ping|chase|finish|complete|fix|write|prepare|test|update|review|build|implement|deploy|submit|send|finali[sz]e|"
    r"create|design|schedule|set up|setup|check|add|remove|refactor|clean|merge|push|draft|document|"
    r"organi[sz]e|plan|research|investigate|look|follow|collect|gather|label|train|evaluate|upload|"
    r"configure|integrate|connect|handle|take|prepare|make|share|book|email|call|contact|ask|talk|"
    r"create|develop|code|run|migrate|improve|optimi[sz]e|polish|ship|release|rewrite|setup|do|work|get|start|"
    r"finali[sz]e|record|present|practice|rehearse|print|print|translate|annotate|analy[sz]e|compare)\b", I)
NON_TASK_START = re.compile(r"^(?:be|use|using|go|going|stick|keep|switch|see|say|think|let|have a|talk about|"
                            r"discuss|cover|look at|move on|continue with|follow the|wait)\b", I)

ACCEPT_RE = re.compile(
    rf"^(?:(?:sure|yes|yeah|yep|okay|ok|alright|fine|will do|no problem|got it|sounds good|absolutely)\b[,.! ]*)*"
    rf"(?:i{_A}ll|i will|i can|let me|i got|i{_A}ve got|will do|on it|leave it to me)?\s*"
    rf"(?:(?:do|handle|take|take care of|own|get|pick up|work on|cover|manage)\s+(?:it|that|this|those|these)|"
    rf"it|that|this|do it|handle it|will do|on it)?\s*[.!]*$", I)
ACCEPT_STRONG_RE = re.compile(
    rf"\b(?:will do|on it|leave it to me|i can (?:do|handle|take|cover|manage) (?:it|that|this)|"
    rf"i{_A}ll (?:do|handle|take|take care of|get|own|pick up|work on|cover|manage) (?:it|that|this)|"
    rf"i will (?:do|handle|take|take care of|get|own|pick up|work on|cover|manage) (?:it|that|this)|"
    rf"let me (?:do|handle|take) (?:it|that|this)|i got (?:it|this|that))\b", I)
ACCEPT_WEAK_RE = re.compile(r"^(?:sure|yes|yeah|yep|okay|ok|alright|fine|no problem|got it|absolutely)\b[,.! ]*$", I)

REQUEST_NAMED = re.compile(
    r"^(?:(?:hey|so|okay|ok|and)[, ]+)?(?P<owner>{names})\s*[,:]?\s*(?:(?:can|could|would|will) you|please)(?: please)?\s+(?P<task>.+)$", I)
REQUEST_UNNAMED = re.compile(
    r"^(?:(?:hey|so|okay|ok|and)[, ]+)?(?:(?:can|could|would|will) you(?: please)?|please)\s+(?P<task>.+)$", I)

# ---------------------------------------------------------- issues / blocks
ISSUE_STRONG_RE = re.compile(
    rf"\b(blocked|blocker|blocking|blocks|broken|breaks|failing|fails|failed|failure|crash(?:es|ing|ed)?|error|errors|"
    rf"exception|bugs?|buggy|not working|doesn{_A}?t work|isn{_A}?t working|aren{_A}?t working|stopped working|"
    rf"won{_A}?t (?:start|load|work|run|build|compile|connect)|can{_A}?t (?:connect|log ?in|deploy|access|run|build|proceed|"
    rf"test|start|get|reach|load)|cannot (?:connect|login|deploy|access|run|build|proceed|test|start)|"
    rf"stuck|delayed|behind schedule|running late|over budget|out of budget|timeouts?|timing out|unavailable|"
    rf"stalled|no access|still (?:not|failing|broken)|keeps? (?:crashing|failing|breaking|timing out)|"
    rf"throwing|throws)\b", I)
ISSUE_WEAK_RE = re.compile(
    r"\b(issues?|problems?|concerns?|risks?|risky|slow|missing|lacking|pending|unresolved|waiting (?:for|on)|"
    r"too (?:costly|expensive|slow|complex|difficult|risky)|difficult|down|late|worried)\b", I)
ISSUE_RESOLVED_RE = re.compile(
    rf"\b(fixed|resolved|solved|sorted(?: out)?|working (?:now|again|fine)|is back|are back|no longer|"
    rf"got it working|patched|it works now|works now|deployed (?:the )?fix)\b", I)
DONE_RE = re.compile(
    rf"\b(?:(?:i{_A}ve|i have|we{_A}ve|we have|has|have|just|already)\s+)?(finished|completed|done with|wrapped up|"
    rf"submitted|merged|shipped|delivered|is done|are done|is complete|are complete|is ready|are ready|"
    rf"has been (?:done|completed|finished|merged)|have been (?:done|completed|finished|merged)|all done|got it done)\b", I)
UNFINISHED_RE = re.compile(r"\b(not (?:yet )?(?:done|finished|complete|ready)|still (?:working|pending|not)|yet to)\b", I)

BLOCK_BECAUSE_RE = re.compile(
    rf"^(?P<impact>.+?)\s+(?:is|are|was|were|got|gets|remains?)?\s*(?:currently |still |now )?blocked\s+(?:because(?: of)?|by|due to|on|until|as)\s+(?P<problem>.+)$", I)
BLOCKING_RE = re.compile(
    rf"^(?P<problem>.+?)\s+(?:is|are|was|keeps?)?\s*(?:currently |still |now )?(?:blocking|holding up|delaying|stopping|preventing)\s+(?P<impact>.+)$", I)
CANT_UNTIL_RE = re.compile(
    rf"\b(?:can{_A}?t|cannot|couldn{_A}?t|unable to|won{_A}?t be able to|not able to)\s+(?P<impact>.+?)\s+(?:until|before|without|till|unless)\s+(?P<problem>.+)$", I)
WAITING_RE = re.compile(
    rf"^(?P<impact>.+?)\s+(?:is|are)?\s*(?:waiting|depends?|dependent)\s+(?:for|on|upon)\s+(?P<problem>.+)$", I)
IMPACT_CLAUSE_RE = re.compile(
    r"(?:,|;|—|-|\bwhich\b|\bso\b|\band\b)\s*(?:that |it |this )?(?:means?|delays?|blocks?|prevents?|stops?|slows?|affects?|"
    r"breaks?|impacts?|holds? up|puts?|pushes?|risks?)\b\s*(?P<impact>.+)$", I)

DEPENDS_RE = re.compile(
    rf"^(?P<second>.+?)\s+(?:depends?|is dependent|are dependent|relies|rely)\s+(?:on|upon)\s+(?P<first>.+)$", I)
AFTER_RE = re.compile(
    rf"^(?:only )?(?:after|once|when|as soon as)\s+(?P<first>.+?),\s*(?:we|i|then|you|they|\w+)\s*(?:can|will|{_A}ll|could|should|need to|must)?\s*(?P<second>.+)$", I)
THEN_AFTER_RE = re.compile(
    rf"^(?P<second>.+?)\s+(?:only )?(?:after|once|as soon as|when|until)\s+(?P<first>.+)$", I)

# ---------------------------------------------------------------- revisions
REVISION_RE = re.compile(
    rf"\b(actually|instead|change of plan|scrap that|switch(?:ing)? to|rather than|on second thought|never ?mind|"
    rf"revised|new (?:plan|deadline|date)|we changed|changed (?:to|my mind)|pushed? (?:it )?(?:back|out)|"
    rf"push(?:ed|ing)?|mov(?:e|ed|ing)|postpone[ds]?|postponing|delay(?:ed|ing)?|extend(?:ed|ing)?|"
    rf"reschedul(?:e|ed|ing)|bring(?:ing)? forward|brought forward|now due|now on|now by|moved up|pulled in|"
    rf"deadline (?:is|was) (?:now|changed)|more time|need(?:s|ed)? (?:until|more time))\b", I)
PURE_DEADLINE_SHIFT_RE = re.compile(
    r"\b(push(?:ed|ing)?|mov(?:e|ed|ing)|postpone[ds]?|postponing|reschedul(?:e|ed|ing)|bring(?:ing)? forward|brought forward|"
    r"extend(?:ed|ing)?|delay(?:ed|ing)?|now due|new (?:deadline|date)|pulled in|moved up)\b", I)

# generic words ignored when comparing tasks
GENERIC_TASK_WORDS = {"deadline", "due", "date", "task", "thing", "stuff", "work", "part", "item", "one",
                      "week", "day", "friday", "monday", "tuesday", "wednesday", "thursday", "saturday",
                      "sunday", "today", "tomorrow", "tonight", "morning", "afternoon", "evening", "time",
                      "plan", "project", "team", "guy", "need", "want", "go", "do", "make", "get"}

PRONOUN_TASK_RE = re.compile(r"^(?:it|that|this|those|these|them|that one|this one)(?:\s+(?:up|out|too|also|then|today|tomorrow|tonight).*)?$", I)


def is_hedged(text: str) -> bool:
    return bool(HEDGE_RE.search(text))


def is_question(text: str) -> bool:
    t = text.strip()
    return t.endswith("?") or bool(QUESTION_START_RE.match(t) and "?" in t)


def clean_task(task: str) -> str:
    """Tidy a captured task phrase for display (does not change meaning)."""
    task = re.sub(r"\s+", " ", task)
    task = re.split(r",\s*(?:but|though|however|although)\b", task, maxsplit=1, flags=I)[0]
    task = task.strip(" ,.;:!?-–—")
    task = re.sub(r"^(?:to\s+)?(?:also\s+|then\s+|first\s+|just\s+|please\s+|go ahead and\s+|try to\s+)+", "", task, flags=I)
    task = re.sub(r"^(?:to\s+)", "", task, flags=I)
    return task.strip(" ,.;:!?-–—")
