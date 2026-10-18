# Survey Instrument (v0.1 — to be piloted in Week 6)

Anonymous online questionnaire (Google Forms / Microsoft Forms). Estimated completion time: 10–15 minutes.
Responses are exported to CSV with the column names below and processed by `src/benchmark.py`.

## Block A — Consent
| Column | Question | Coding |
|---|---|---|
| `consent` | I have read the information sheet and agree to take part voluntarily and anonymously. | `yes` / `no` (no → survey ends) |

## Block B — Background (independent & controlled variables)
| Column | Question | Coding |
|---|---|---|
| `major` | What is your major? | free text |
| `major_group` | Derived from `major` | `IT` (CS, IS, Cybersecurity, SE) / `NonIT` |
| `academic_year` | Year of study | 1–4 |
| `age` | Age | integer |
| `prior_training` | Have you ever completed a cybersecurity or phishing-awareness course/training? | 1 = yes, 0 = no |
| `training_hours` | Approximately how many hours in total? | integer, 0 if none |
| `digital_literacy` | How would you rate your general computer / internet skills? | 1 (very low) – 5 (very high) |
| `self_confidence` | How confident are you that you can recognise a phishing message? | 1 (not at all) – 7 (completely) |

## Block C — 18 Vignettes (dependent variables)
Each vignette is a screenshot-style mock-up (email, SMS or messenger) using a **fictitious** university and
fictitious services. For every vignette the respondent answers two questions:

* `Vxx` — *Is this message phishing or legitimate?* → 1 = phishing, 0 = legitimate
* `Cxx` — *How sure are you?* → 50 % (pure guess) … 100 % (completely sure), in steps of 10

Item order is randomised per respondent. The answer key lives in `configs/config.yaml`.

| Item | Cue | Channel | Key | Scenario (short description) |
|---|---|---|---|---|
| V01 | urgency | email | phishing | "Your university account will be locked in 2 hours" — link to a look-alike login domain |
| V02 | authority | email | phishing | "Dean's office" demands you confirm your student ID and password via an external form |
| V03 | familiarity | messenger | legit | Group-mate shares the official course-page link inside the existing class chat |
| V04 | urgency | sms | legit | Bank one-time code you just requested, with "do not share this code" warning, no link |
| V05 | familiarity | messenger | phishing | "Friend" from a new number asks you to vote for them via a link that requests your messenger login |
| V06 | authority | sms | phishing | "Tax authority": unpaid fine, pay today through a shortened link |
| V07 | urgency | sms | phishing | "Parcel held at customs — pay a small fee within 24 h" with a link |
| V08 | authority | email | legit | IT department announces planned maintenance; no links, refers to the official portal by name |
| V09 | familiarity | email | phishing | "Shared document from your lecturer" — sender display name matches, address domain does not |
| V10 | urgency | email | phishing | "Scholarship payment fails unless you update bank details today" |
| V11 | authority | email | phishing | "Rector" asks you personally to buy gift cards for an event and send the codes |
| V12 | familiarity | email | legit | Library notice about a book you actually borrowed, sent from the official domain |
| V13 | urgency | email | legit | Exam registration closes tomorrow — official university domain, links to the known portal |
| V14 | familiarity | sms | phishing | "Hi, it's me, I lost my phone, this is my new number — can you send me money?" |
| V15 | authority | email | legit | Registrar confirms your transcript request that you submitted, reference number included |
| V16 | urgency | messenger | phishing | "Your account will be deleted in 1 hour for violations — appeal here" |
| V17 | authority | messenger | phishing | "Official support" account asks for the verification code you just received |
| V18 | familiarity | email | phishing | Fake "password reset" from a popular streaming service you might use, look-alike domain |

Design: every cue type has **4 phishing + 2 legitimate** items, so per-cue accuracy is not confounded by the
share of phishing items and false alarms (over-suspicion) are measured, not only misses.

## Block D — Attention check
| Column | Question | Coding |
|---|---|---|
| `attention_check` | "To show that you are reading carefully, please select *Strongly agree* (5)." | expected = 5 |

`completion_seconds` is taken from the form platform's start/finish timestamps.
