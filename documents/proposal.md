<!--
WORKING TEMPLATE. Delete this comment block before submitting.

IST 707 project proposal. Due Tuesday, September 15, 2026.
Deliverable: this file, proposal.md, in this repository, with McSweeney (pjmcswee) added as a collaborator.

HARD LIMIT: two to three pages. Shorter is allowed. Longer is not.
Rough budget to stay inside it: Introduction ~400 words, Literature Review ~450 words
(stakeholders included), Data and Methods ~450 words, Risks ~300 words, plus the plan table.

GRADING, 50 points:
  10  every listed section present. Presence only. Quality is not checked here.
      People lose these points purely by leaving a section out. Never delete a heading.
  10  stakeholders and their needs clearly identified (they live in the Literature Review).
  20  the five Heilmeier Catechism questions answered effectively.
  10  plan is feasible with enough detail to give confidence.

WHO WRITES WHAT, agreed September 11, 2026:
  Hashim Khan  -> Introduction, Literature Review
  Tyler Katz   -> Data and Methods
  Mrgaj Iyer   -> Project Plan, Risks

TWO STANDING RULES FROM THE RUBRIC:
  1. Weekly commit history is inspected and graded. Commit early, commit often,
     and make sure the work is visibly spread across all three of us.
  2. Citations must be real and must use GitHub footnote syntax. Find them on
     Google Scholar. Do not cite anything secondhand out of the project brief.

SOURCE MATERIAL: IST707_Project_Brief_DriveFailure.docx, one directory up from the repo.
It holds the verified data numbers, draft answers to all five Heilmeier questions,
and seven risks with mitigations. It is working material, not submission text.
Rewrite it in our own voice rather than pasting it.
-->

# Predicting Hard Drive Failure from Fleet Telemetry

<!-- Working title. Short, and enough for McSweeney to know roughly what this is. Change it if the team prefers something else. -->

## Team

| Name | GitHub ID | Role |
| --- | --- | --- |
| Tyler Katz | `tkatz123` | Point of contact, repository owner |
| Hashim Khan | `TBD` | Team member |
| Mrgaj Iyer | `TBD` | Team member |

<!--
The rubric requires full names, every member's GitHub id, and an explicitly named
point of contact who owns the repository.
Tyler is listed as point of contact because he created the repo. Say so if you want it changed.
BLOCKER: two GitHub ids are still missing and the rubric asks for them by name.
Fill them in and add all three plus pjmcswee as collaborators before Tuesday.
-->

**Point of contact:** Tyler Katz.

## Introduction

<!--
OWNER: Hashim Khan.
Three of the five Heilmeier questions get answered here. Keep the three sub-answers
distinct so a grader can find each one. No jargon at all in the first one: write it
so someone outside the class understands what we are doing.
Draft answers for all three are in section 3 of the brief.
-->

### What are we trying to do?

<!-- Heilmeier 1. Objectives in absolutely no jargon. No "model", no "features", no "classifier". -->

_To be written._

### What is new in our approach, and why do we think it will succeed?

<!-- Heilmeier 3. Brief here. The detail belongs in Data and Methods. The brief argues three points: probability over a window instead of a threshold alarm, sensors used together and over time, and far more labelled data than the 2007 studies had. -->

_To be written._

### Who cares, and what difference will it make?

<!-- Heilmeier 4. Name who benefits and what changes for them. This sets up the stakeholder list below, so keep the two consistent. -->

_To be written._

## Literature Review

<!--
OWNER: Hashim Khan.
This section carries 20 of the 50 points between the Heilmeier answer and the stakeholders,
so it is the highest-value section in the document.
-->

### How is it done today, and what are the limits of current practice?

<!--
Heilmeier 2. Review what has already been tried, with real citations, or cite literature
showing the method is novel. Google Scholar.
The two anchor papers are both from 2007 and both study large real fleets:
Pinheiro, Weber and Barroso (Google), and Schroeder and Gibson (Carnegie Mellon).
Look them up properly and cite the real records. Do not take the details from the brief.
Footnote syntax, which GitHub renders:
    ... a large fraction of drives fail with no prior warning.[^pinheiro2007]
    [^pinheiro2007]: Author, A., Author, B. "Title." *Venue*, Year. URL
-->

_To be written._

### Stakeholders and their needs

<!--
Worth 10 points on its own. For each stakeholder, state three things explicitly:
who they are, why they are a stakeholder, and what they specifically need.
McSweeney's own example of the shape he wants: "a city traffic planner needs to know about
temporal variation in pedestrian traffic and office building density in order to place traffic signals."
No interviews expected, but some online research is.
Whatever we say they need has to match what the evaluation in Data and Methods measures.
The brief lists four candidates: data center operators, smaller enterprise IT teams,
Backblaze and similar providers, and drive manufacturers.
-->

- **[Stakeholder]:** _why they are a stakeholder, and what they specifically need._
- **[Stakeholder]:** _why they are a stakeholder, and what they specifically need._
- **[Stakeholder]:** _why they are a stakeholder, and what they specifically need._
- **[Stakeholder]:** _why they are a stakeholder, and what they specifically need._

## Data and Methods

<!-- OWNER: Tyler Katz. -->

### Data

<!--
The rubric asks for four things here:
  1. A link to the data.
  2. Summary information: row count, column count, feature types.
  3. Provenance. How do we know it is reliable? Does it carry metadata, and if not,
     what else do we know about it?
  4. If more than one dataset is needed, name each and give evidence it is available.
Section 2 of the brief has every number already, measured from a real downloaded quarter
rather than quoted from documentation. Say that plainly: it is the strongest thing
this proposal can claim about its own data.
Include the licence terms and the absence of PII.
-->

_To be written._

### Methods

<!--
Three parts, all required:
  1. Transformations and preprocessing. The big one is collapsing daily snapshots into a
     per-drive-per-window table. That is the first engineering milestone, not an afterthought.
  2. Modeling techniques to be applied. Include the baselines we compare against,
     not just the models we hope will win.
  3. How the models will be evaluated, and the evaluation MUST be consistent with the
     stakeholder needs stated above. This is where the two sections have to agree.
     Accuracy is meaningless at one failure in 26,000 drive-days. Say why, and say what
     we use instead.
No code in the proposal.
-->

_To be written._

## Project Plan

<!--
OWNER: Mrgaj Iyer.
Roughly two months of work. Final report is due the first week of December.
McSweeney explicitly suggests a table, so use one. 10 points ride on this looking feasible
with enough detail to give confidence, which means real activities and a checkable milestone
per period, not "work on model" repeated five times.
Sanity check it against the risks section: if the data volume risk is real, the schedule
has to show time for it.
-->

| Period | Activity | Milestone |
| --- | --- | --- |
| _dates_ | _what happens_ | _what exists at the end of it_ |
| _dates_ | _what happens_ | _what exists at the end of it_ |
| _dates_ | _what happens_ | _what exists at the end of it_ |
| _dates_ | _what happens_ | _what exists at the end of it_ |
| Week of Dec 1 | Final report and presentation | Report submitted |

## Risks

<!--
OWNER: Mrgaj Iyer.
This is Heilmeier 5, so it is worth real points rather than being a formality.
For each risk give three things: the pitfall, how we mitigate it, and what we do if
that part of the plan fails outright.
Section 4 of the brief has seven of them written out. The most interesting one, and the
one most likely to impress, is that the missing sensor columns are missing in a pattern
that tracks manufacturer rather than chance, so a careless model learns brand instead of health.
Do not minimise these. The rubric rewards identifying them honestly.
-->

- **[Risk]:** _what could go wrong. **Mitigation:** how we reduce it. **If it fails:** what we do instead._
- **[Risk]:** _what could go wrong. **Mitigation:** how we reduce it. **If it fails:** what we do instead._
- **[Risk]:** _what could go wrong. **Mitigation:** how we reduce it. **If it fails:** what we do instead._

## References

<!--
GitHub renders footnotes wherever they are defined, but keeping them here keeps the file tidy.
Every citation must be real and verified on Google Scholar. The syllabus warns explicitly
that AI tools invent plausible citations that do not exist, so check each one resolves
to a real paper before this is submitted.
-->

[^placeholder]: Author, A., Author, B. "Title." *Venue*, Year. URL

---

<!--
REQUIRED BY THE SYLLABUS. Do not delete this. Edit it to say what actually happened.
The AI use policy permits AI tools but requires all submitted work to document if and how
they were used, identifying AI-generated writing in a footnote or endnote. Failure to
acknowledge it counts as academic dishonesty.
Separately: grading is contingent on being able to verbally support this work in class,
so every one of us needs to be able to defend our own section out loud.
-->

**Use of AI tools:** _state here which tools were used, by whom, and for what (for example: structuring this document, editing prose, locating literature). Verify before submission that this describes what actually happened._
