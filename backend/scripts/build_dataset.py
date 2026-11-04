"""Build the labelled sentence dataset used to train/evaluate the classifier.

HONEST DESCRIPTION OF THE DATA
------------------------------
The sentences are *synthetic*: each class has hand-written sentence templates
with slots (people, tasks, technologies, dates ...).  Every template is filled
with several random slot values, with some informal noise (lower-casing,
dropped punctuation).

Leakage control: the train / validation / test split is done **by template**,
never by individual sentence.  All fillings of one template land in the same
split, so the test set never contains a re-worded copy of a training sentence
(only different phrasings / structures).  Even so, template-generated text is
much easier and cleaner than real meeting speech, so scores on the synthetic
test split are an optimistic upper bound.  A separate, small, hand-written set
(`handwritten_eval.csv`, never used for training) is reported alongside.

Run:  python scripts/build_dataset.py
"""
import csv
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.config import DATASET_PATH  # noqa: E402

SEED = 42
FILLS_PER_TEMPLATE = 7

PEOPLE = ["Sriya", "Rahul", "Ananya", "Kiran", "Meera", "Arjun", "Priya", "Dev", "Neha", "Vikram"]
TASKS = ["the login page", "the dashboard", "the API documentation", "the database schema", "the unit tests",
         "the project report", "the landing page", "the deployment script", "the user survey",
         "the presentation slides", "the data cleaning script", "the search feature", "the onboarding flow",
         "the payment module", "the mobile layout", "the export feature", "the analytics charts"]
VERBS = ["finish", "update", "review", "test", "prepare", "write", "fix", "deploy", "send", "complete", "draft", "check"]
DAYS = ["Friday", "Monday", "tomorrow", "next week", "Wednesday", "end of day", "tonight", "Thursday", "the 14th"]
TECHS = ["React", "PostgreSQL", "SQLite", "MongoDB", "Docker", "FastAPI", "Redis", "Firebase", "Vue", "AWS", "Flask", "MySQL"]
COMPS = ["frontend", "backend", "database", "testing", "deployment", "authentication", "documentation"]
SUBJS = ["the API", "the login page", "the build", "the database connection", "the deployment", "the test suite",
         "the server", "the payment module", "the search endpoint", "the CI pipeline", "the staging site", "the mobile app"]
NUMS = ["three", "four", "five", "six", "eight", "twelve", "ten"]
TIMES = ["ten", "eleven thirty", "two", "four", "nine"]

T = {
"ACTION": [
 "I will {v} {task} by {day}.", "I'll {v} {task} {day}.", "{person} will {v} {task}.",
 "{person} needs to {v} {task} before {day}.", "Please {v} {task} by {day}.", "{person}, can you {v} {task}?",
 "Can you {v} {task} by {day}?", "We need to {v} {task} before the review.", "I'm going to {v} {task} tonight.",
 "{person} is responsible for {task}.", "{person} will take care of {task}.", "Let me {v} {task} and send it over.",
 "I can take {task} if nobody else wants it.", "{person} has to {v} {task} by {day}.", "I'll try to {v} {task} by {day}.",
 "{task} is assigned to {person}.", "Action item: {person} to {v} {task}.", "gonna {v} {task} {day} then",
 "I need to {v} {task} before {day}.", "We have to {v} {task} by {day}.", "{person} should {v} {task} once the design is approved.",
 "I'll set up {task} and let everyone know.", "Someone needs to {v} {task}.", "I'll follow up with {person} about {task}.",
 "{person} is going to {v} {task} {day}.", "I'll take {task}.", "Sure, I'll {v} {task}.", "I can {v} {task} by {day}.",
 "The team must {v} {task} by {day}.", "{person} and {person2} will {v} {task}.", "i'll {v} {task} {day} no worries",
 "{person}, please {v} {task} when you get a chance.",
],
"DECISION": [
 "We decided to use {tech} for {comp}.", "Let's go with {tech}.", "We agreed to move {task} to {day}.",
 "The final decision is to use {tech}.", "Okay, we'll stick with {tech} for {comp}.", "It's settled, we are going with {tech}.",
 "We've agreed that {person} will lead {comp}.", "Decision: use {tech} for {comp}.", "Fine, let's use {tech} for now.",
 "We approved the plan to {v} {task}.", "We're going with {tech}.", "The team agreed to drop {tech}.",
 "Let's move the review to {day}.", "We will use {tech} instead of {tech2}.", "Everyone agreed, the deadline stays at {day}.",
 "So it's decided, {task} goes first.", "We chose {tech} over {tech2} for {comp}.", "Let's stick with {tech}.",
 "It was agreed that the demo will be on {day}.", "We'll go with {tech} and revisit later.", "Agreed, we are switching to {tech}.",
 "Final call: {tech} for {comp}.", "The plan is to launch on {day}.", "We decided to skip {task} this sprint.",
 "Okay, decision made, {person} owns {comp}.", "We've decided to postpone {task} until {day}.",
 "Let's keep {tech} as the {comp} choice.", "decided to use {tech}, moving on", "Alright, we are moving forward with {tech}.",
 "We settled on {tech} for {comp}.", "Okay so we're dropping {task} from the first release.",
],
"ISSUE": [
 "{subj} is not working.", "{subj} keeps crashing.", "We are blocked by {subj}.", "There is a bug in {subj}.",
 "{subj} is failing with a timeout error.", "{subj} is delayed because of the vendor.", "I'm stuck on {subj}.",
 "Testing is blocked because {subj} is broken.", "We have a problem with {subj}.", "{subj} is too slow for production.",
 "The build failed again because of {subj}.", "{subj} throws an error whenever we deploy.", "We are behind schedule on {task}.",
 "{subj} is still broken after the update.", "I can't access {subj}.", "We don't have enough budget for {tech}.",
 "{subj} is a major risk for the release.", "There's a serious problem with {subj}.", "{subj} stopped working after the merge.",
 "{subj} is returning a 500 error.", "The main concern is that {subj} might not be ready.", "{subj} is running late.",
 "The client is unhappy with {subj}.", "{subj} won't load on mobile.", "{subj} is still failing.",
 "We still have a memory leak in {subj}.", "Nobody has access to {subj}.", "{subj} is timing out under load.",
 "{task} is blocked until {subj} is fixed.", "the {comp} is a mess right now, nothing works",
],
"SUGGESTION": [
 "Maybe we should use {tech} for {comp}.", "What if we {v} {task} earlier?", "Could we try {tech} instead?",
 "I suggest we {v} {task} before {day}.", "Perhaps {person} could {v} {task}.", "How about using {tech} for {comp}?",
 "We could split {task} into two parts.", "Why don't we move the review to {day}?", "It might be better to use {tech}.",
 "Should we consider {tech} for {comp}?", "I think we should add {task}.", "One option is to use {tech} here.",
 "Alternatively, we could outsource {task}.", "What about trying {tech}?", "maybe we can {v} {task} together",
 "We might want to {v} {task} sooner.", "I propose we meet on {day} to {v} {task}.",
 "Would it be better to use {tech} instead of {tech2}?", "Perhaps we can postpone {task}.", "I'd suggest starting with {task}.",
 "It could help if {person} reviews {task}.", "We can also try {tech} for {comp}.", "Let's consider {tech}.",
 "Why not use {tech}?", "Maybe {person} can pair with me on {task}.", "an idea: we {v} {task} using {tech}",
 "Worth considering {tech} for {comp}.", "Perhaps we should {v} {task} first.", "Do you think we could drop {tech}?",
 "maybe use {tech} here?",
],
"INFORMATION": [
 "{task} is ready.", "The meeting starts at {time}.", "The {comp} uses {tech}.", "The project has {num} team members.",
 "{subj} is running on {tech}.", "The database contains {num} tables.", "{person} joined the project last month.",
 "I finished {task} yesterday.", "The demo is on {day}.", "We have {num} open tickets.", "The client is based in Mumbai.",
 "The last release went out on {day}.", "{task} was completed last sprint.", "Our current stack is {tech} and {tech2}.",
 "{person} is on leave until {day}.", "The server has {num} gigabytes of memory.", "The sprint ends on {day}.",
 "The report covers {comp} and {comp2}.", "I updated {task} this morning.", "The test coverage is around {num} percent.",
 "{subj} is deployed on {tech}.", "The call today is about {comp}.", "That is the end of the first section.",
 "We have been using {tech} since last year.", "okay thanks everyone", "yeah that makes sense", "Last week we covered {comp}.",
 "{person} presented the {comp} update.", "Right, so that covers the agenda.", "good morning everyone",
],
"QUESTION": [
 "What is the status of {task}?", "Who is working on {task}?", "When is {task} due?", "Is {subj} working now?",
 "Do we have access to {tech}?", "Did {person} finish {task}?", "Which {comp} framework are we using?",
 "How long will {task} take?", "Are we still on track for {day}?", "Who owns {comp}?", "Why is {subj} failing?",
 "Has anyone tested {task}?", "Where is {task} stored?", "what's the deadline for {task}",
 "Can someone explain how {tech} works?", "Is the {comp} ready for the demo?", "How many users are we expecting?",
 "Do you know who is handling {comp}?", "When does the sprint end?", "What did we decide about {tech}?",
 "Is {person} joining today?", "Does anyone know if {subj} is fixed?", "Who is presenting on {day}?",
 "What happens if {subj} fails?", "Are there any blockers for {task}?", "did {person} send the invite",
 "Is {tech} free to use?", "How is {person} doing with {task}?", "Any updates on {subj}?",
 "so when do we need {task} again?",
],
}


def noisy(text: str, rng: random.Random) -> str:
    r = rng.random()
    if r < 0.18:
        return text.lower()
    if r < 0.30:
        return text.rstrip(".?!")
    return text


def fill(template: str, rng: random.Random) -> str:
    people = rng.sample(PEOPLE, 2)
    techs = rng.sample(TECHS, 2)
    comps = rng.sample(COMPS, 2)
    values = dict(
        person=people[0], person2=people[1], task=rng.choice(TASKS), v=rng.choice(VERBS), day=rng.choice(DAYS),
        tech=techs[0], tech2=techs[1], comp=comps[0], comp2=comps[1], subj=rng.choice(SUBJS),
        num=rng.choice(NUMS), time=rng.choice(TIMES),
    )
    text = template.format(**values)
    return text[0].upper() + text[1:] if text[0].islower() and rng.random() < 0.7 else text


def main() -> None:
    rng = random.Random(SEED)
    rows = []
    for label, templates in T.items():
        order = templates[:]
        rng.shuffle(order)
        n = len(order)
        n_test, n_val = max(1, round(n * 0.2)), max(1, round(n * 0.2))
        splits = {}
        for i, t in enumerate(order):
            splits[t] = "test" if i < n_test else "validation" if i < n_test + n_val else "train"
        for tid, t in enumerate(templates):
            seen = set()
            for _ in range(FILLS_PER_TEMPLATE * 3):
                s = noisy(fill(t, rng), rng)
                if s in seen:
                    continue
                seen.add(s)
                rows.append((s, label, f"{label[:3]}-{tid:02d}", splits[t]))
                if len(seen) >= FILLS_PER_TEMPLATE:
                    break

    # safety: an identical sentence must never appear in two splits
    owner = {}
    cleaned = []
    for text, label, tid, split in rows:
        key = text.strip().lower().rstrip(".?!")
        if key in owner and owner[key] != split:
            continue
        owner[key] = split
        cleaned.append((text, label, tid, split))

    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATASET_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["text", "label", "template_id", "split"])
        w.writerows(cleaned)

    from collections import Counter
    print(f"wrote {len(cleaned)} rows to {DATASET_PATH}")
    print(Counter(r[3] for r in cleaned))
    print(Counter((r[1], r[3]) for r in cleaned))


if __name__ == "__main__":
    main()
