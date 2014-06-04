# regexgolf for mobile vs desktop browser's User-Agents

The shortest regular expression that can match a mobile browser's
User-Agent, generated from two lists: one of known mobile user-agents,
and one of known non-mobile user-agents.

Dataset based on available mobile browsers in Chrome's emulation:
https://developer.chrome.com/devtools/docs/mobile-emulation

Code is hacked up version of Peter Norvig's Regular Expression golf program at
http://nbviewer.ipython.org/url/norvig.com/ipython/xkcd1313-part2.ipynb?create=1

# Spoiler:

* Test for mobile user-agent: `/u|an/i`

* Test for desktop user-agent: `/ i?.t/i﻿`

# Online checker for the solution:

* http://goo.gl/pwzmL6

* http://goo.gl/nE45NJ

