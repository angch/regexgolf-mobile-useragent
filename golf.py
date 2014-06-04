from __future__ import division
import re
import time
import random
import __builtin__
from __builtin__ import any, all, sum # (because ipython imports the numpy versions)
from collections import Counter

def verify(regex, winners, losers):
    "Return true iff the regex matches all winners but no losers."
    missed_winners = {W for W in winners if not re.search(regex, W)}
    matched_losers = {L for L in losers if re.search(regex, L)}
    if missed_winners:
        print "Error: should match but did not:", ', '.join(missed_winners)
    if matched_losers:
        print "Error: should not match but did:", ', '.join(matched_losers)
    return not (missed_winners or matched_losers)

def bb_findregex(winners, losers, calls=10000, restarts=10):
    "Find the shortest disjunction of regex components that covers winners but not losers."
    solution = '^(' + OR(winners) + ')$'
    bb = BranchBoundRandom(solution, calls)
    covers = eliminate_dominated(regex_covers(winners, losers))
    for restart in range(restarts):
        bb.calls = calls
        bb.search(covers.copy())
        if bb.calls > 0: 
            return bb # If search was not cut off, then stop
    return bb

class BranchBoundRandom(object):

    def __init__(self, solution, calls):
        self.solution, self.calls = solution, calls

    def search(self, covers, partial=None):
        """Recursively extend partial regex until it matches all winners in covers.
        Try all reasonable combinations until we run out of calls."""
        if self.calls <= 0: 
            return partial, covers
        self.calls -= 1
        covers, partial = simplify_covers(covers, partial)
        if not covers: # Nothing left to cover; solution is complete
            self.solution = min(partial, self.solution, key=len)
        elif len(OR(partial, min(covers, key=len))) < len(self.solution):
            # Try with and without the greedy-best component
            K = random.choice((2, 3, 4, 4, 5, 6))
            F = random.choice((1., 1., 2.))
            def score(c): return K * len(covers[c]) - len(c) + random.uniform(0., F)
            best = max(covers, key=score) # Best component
            covered = covers[best] # Set of winners covered by r
            covers.pop(best)
            self.search({c:covers[c]-covered for c in covers}, OR(partial, best))
            self.search(covers, partial)
        return self.solution

def regex_covers(winners, losers):
    """Generate regex components and return a dict of {regex: {winner...}}.
    Each regex matches at least one winner and no loser."""
    losers_str = '\n'.join(losers)
    wholes = {'^'+winner+'$' for winner in winners}
    parts = {d for w in wholes for p in subparts(w) for d in dotify(p)}
    chars = set(cat(winners))
    pairs = {A+'.'+q+B for A in chars for B in chars for q in rep_chars}
    reps = {r for p in parts for r in repetitions(p)}
    pool = wholes | parts | pairs | reps                         
    searchers = [re.compile(c, re.MULTILINE).search for c in pool]
    return {r: set(filter(searcher, winners)) 
            for (r, searcher) in zip(pool, searchers)
            if not searcher(losers_str)}

def repetitions(part):
    """Return a set of strings derived by inserting a single repetition character ('+' or '*' or '?') 
    after each non-special character.  Avoid redundant repetition of dots."""
    splits = [(part[:i], part[i:]) for i in range(1, len(part)+1)]
    return {A + q + B 
            for (A, B) in splits
            # Don't allow '^*' nor '$*' nor '..*' nor '.*.'
            if not (A[-1] in '^$')
            if not A.endswith('..')
            if not (A.endswith('.') and B.startswith('.'))
            for q in rep_chars}

rep_chars = ('*', '+', '?')

def simplify_covers(covers, partial=None):
    "Eliminate dominated regexes, and select ones that uniquely cover a winner."
    previous = None
    while covers != previous:
        previous = covers
        covers = eliminate_dominated(covers)
        covers, necessary = select_necessary(covers)
        partial = OR(partial, necessary)
    return covers, partial

def eliminate_dominated(covers):
    """Given a dict of {regex: {winner...}}, make a new dict with only the regexes
    that are not dominated by any others. A regex r is dominated by r2 if r2 covers 
    a superset of the matches covered by r, and r2 is shorter."""
    newcovers = {}
    def signature(r): return (-len(covers[r]), len(r))
    for r in sorted(covers, key=signature):
        if not covers[r]: break # All remaining r must not cover anything
        # r goes in newcache if it is not dominated by any other regex
        if not any(covers[r2] >= covers[r] and len(r2) <= len(r) 
                   for r2 in newcovers):
            newcovers[r] = covers[r]
    return newcovers

def select_necessary(covers):
    """Select winners covered by only one component; remove from covers.
    Return a pair of (covers, necessary)."""
    counts = Counter(w for r in covers for w in covers[r])
    necessary = {r for r in covers if any(counts[w] == 1 for w in covers[r])}
    if necessary:
        covered = {w for r in necessary for w in covers[r]}
        covers = {r:covers[r]-covered for r in covers if r not in necessary}
        return covers, OR(necessary)
    else:
        return covers, None

def OR(*regexes):
    """OR together component regexes. Ignore 'None' components.
    Allows both OR(a, b, c) and OR([a, b, c]), similar to max."""
    if len(regexes) == 1: 
        regexes = regexes[0]
    return '|'.join(r for r in regexes if r)

subpart_size = 5

def subparts(word):
    "Return a set of subparts of word, consecutive characters up to length 5."
    return set(word[i:i+1+s] for i in range(len(word)) for s in range(subpart_size)) 

def dotify(part):
    "Return all ways to replace a subset of chars in part with '.'."
    if part == '':
        return {''}  
    else:
        return {c+rest for rest in dotify(part[1:]) 
                for c in replacements(part[0])}
       
def replacements(char):
    "Return replacement characters for char (char + '.' unless char is special)."
    if (char == '^' or char == '$'):
        return char
    else:
        return char + '.'

cat = ''.join

def negative_lookahead_solution(W, L): 
    "Find a solution for W but not L by negative lookahead on SOLUTION[L, W]."
    solution = '^(?!.*(' + SOLUTION[L, W] + '))'
    assert verify(solution, W, L)
    return solution

def better_solution(W, L):
    "Return the better of the 'regular' or negative lookahead solutions."
    return min(SOLUTION[W, L], negative_lookahead_solution(W, L),
               key=len)

##############################################################################

def words(text): 
    "Return a set of all words in the text, lowercased."
    return frozenset(text.lower().split())

def phrases(text, sep='/'): 
    "Return a set of all 'sep'-separated phrases in text, uppercased."
    return frozenset(line.strip() for line in text.replace("(", "<").replace(")", ">").replace("+", "_").upper().split(sep))

winners = words('''washington adams jefferson jefferson madison madison monroe 
    monroe adams jackson jackson van-buren harrison polk taylor pierce buchanan 
    lincoln lincoln grant grant hayes garfield cleveland harrison cleveland mckinley
    mckinley roosevelt taft wilson wilson harding coolidge hoover roosevelt 
    roosevelt roosevelt roosevelt truman eisenhower eisenhower kennedy johnson nixon 
    nixon carter reagan reagan bush clinton clinton bush bush obama obama''')

losers = words('''clinton jefferson adams pinckney pinckney clinton king adams 
    jackson adams clay van-buren van-buren clay cass scott fremont breckinridge 
    mcclellan seymour greeley tilden hancock blaine cleveland harrison bryan bryan 
    parker bryan roosevelt hughes cox davis smith hoover landon wilkie dewey dewey 
    stevenson stevenson nixon goldwater humphrey mcgovern ford carter mondale 
    dukakis bush dole gore kerry mccain romney''') - winners

boys = words('jacob mason ethan noah william liam jayden michael alexander aiden')
girls = words('sophia emma isabella olivia ava emily abigail mia madison elizabeth')

nfl_in = words('colts saints chargers 49ers seahawks patriots panthers broncos chiefs eagles bengals packers')
nfl_out = words('''jets dolphins bills steelers ravens browns titans jaguars texans raiders cowboys giants 
    redskins bears lions vikings falcons buccaneers cardinals rams''')

pharma = words('lipitor nexium plavix advair ablify seroquel singulair crestor actos epogen')
cities = words('paris trinidad capetown riga zurich shanghai vancouver chicago adelaide auckland')

foo = words('''afoot catfoot dogfoot fanfoot foody foolery foolish fooster footage foothot footle footpad footway 
    hotfoot jawfoot mafoo nonfood padfoot prefool sfoot unfool''')
bar = words('''Atlas Aymoro Iberic Mahran Ormazd Silipan altared chandoo crenel crooked fardo folksy forest 
    hebamic idgah manlike marly palazzi sixfold tarrock unfold''')

nouns = words('''time year people way day man thing woman life child world school 
    state family student group country problem hand part place case week company 
    system program question work government number night point home water room 
    mother area money story fact month lot right study book eye job word business 
    issue side kind head house service friend father power hour game line end member 
    law car city community name president team minute idea kid body information 
    back parent face others level office door health person art war history party result 
    change morning reason research girl guy moment air teacher force education''')
adverbs = words('''all particularly just less indeed over soon course still yet before 
    certainly how actually better to finally pretty then around very early nearly now 
    always either where right often hard back home best out even away enough probably 
    ever recently never however here quite alone both about ok ahead of usually already 
    suddenly down simply long directly little fast there only least quickly much forward 
    today more on exactly else up sometimes eventually almost thus tonight as in close 
    clearly again no perhaps that when also instead really most why ago off 
    especially maybe later well together rather so far once''') - nouns  
verbs = words('''ask believe borrow break bring buy can be able cancel change clean
    comb complain cough count cut dance draw drink drive eat explain fall
    fill find finish fit fix fly forget give go have hear hurt know learn
    leave listen live look lose make do need open close shut organise pay
    play put rain read reply run say see sell send sign sing sit sleep
    smoke speak spell spend stand start begin study succeed swim take talk
    teach tell think translate travel try turn off turn on type understand
    use wait wake up want watch work worry write''') - nouns

randoms = frozenset(vars(random))
builtins = frozenset(vars(__builtin__)) - randoms

starwars = phrases('''The Phantom Menace / Attack of the Clones / Revenge of the Sith /
    A New Hope / The Empire Strikes Back / Return of the Jedi''')

startrek = phrases('''The Wrath of Khan / The Search for Spock / The Voyage Home /
    The Final Frontier / The Undiscovered Country / Generations / First Contact /
    Insurrection / Nemesis''')

dogs = phrases(''''Labrador Retrievers / German Shepherd Dogs / Golden Retrievers / Beagles / Bulldogs / 
    Yorkshire Terriers / Boxers / Poodles / Rottweilers / Dachshunds / Shih Tzu / Doberman Pinschers / 
    Miniature Schnauzers / French Bulldogs / German Shorthaired Pointers / Siberian Huskies / Great Danes / 
    Chihuahuas / Pomeranians / Cavalier King Charles Spaniels / Shetland Sheepdogs / Australian Shepherds / 
    Boston Terriers / Pembroke Welsh Corgis / Maltese / Mastiffs / Cocker Spaniels / Havanese / 
    English Springer Spaniels / Pugs / Brittanys / Weimaraners / Bernese Mountain Dogs / Vizslas / Collies / 
    West Highland White Terriers / Papillons / Bichons Frises / Bullmastiffs / Basset Hounds / 
    Rhodesian Ridgebacks / Newfoundlands / Russell Terriers / Border Collies / Akitas / 
    Chesapeake Bay Retrievers / Miniature Pinschers / Bloodhounds / St. Bernards / Shiba Inu / Bull Terriers / 
    Chinese Shar-Pei / Soft Coated Wheaten Terriers / Airedale Terriers / Portuguese Water Dogs / Whippets / 
    Alaskan Malamutes / Scottish Terriers / Australian Cattle Dogs / Cane Corso / Lhasa Apsos / 
    Chinese Crested / Cairn Terriers / English Cocker Spaniels / Dalmatians / Italian Greyhounds / 
    Dogues de Bordeaux / Samoyeds / Chow Chows / German Wirehaired Pointers / Belgian Malinois / 
    Great Pyrenees / Pekingese / Irish Setters / Cardigan Welsh Corgis / Staffordshire Bull Terriers / 
    Irish Wolfhounds / Old English Sheepdogs / American Staffordshire Terriers / Bouviers des Flandres / 
    Greater Swiss Mountain Dogs / Japanese Chin / Tibetan Terriers / Brussels Griffons / 
    Wirehaired Pointing Griffons / Border Terriers / English Setters / Basenjis / Standard Schnauzers / 
    Silky Terriers / Flat-Coated Retrievers / Norwich Terriers / Afghan Hounds / Giant Schnauzers / Borzois / 
    Wire Fox Terriers / Parson Russell Terriers / Schipperkes / Gordon Setters / Treeing Walker Coonhounds''')
cats = phrases('''Abyssinian / Aegean cat / Australian Mist / American Curl / American Bobtail / 
    American Polydactyl / American Shorthair / American Wirehair / Arabian Mau / Asian / Asian Semi-longhair / 
    Balinese / Bambino / Bengal / Birman / Bombay / Brazilian Shorthair / British Shorthair / British Longhair / 
    Burmese / Burmilla / California Spangled Cat / Chantilly/Tiffany / Chartreux / Chausie / Cheetoh / 
    Colorpoint Shorthair / Cornish Rex / Cymric / Cyprus cat / Devon Rex / Donskoy or Don Sphynx / Dragon Li / 
    Dwelf / Egyptian Mau / European Shorthair / Exotic Shorthair / German Rex / Havana Brown / Highlander / 
    Himalayan-Colorpoint Persian / Japanese Bobtail / Javanese / Khao Manee / Korat / Korn Ja / 
    Kurilian Bobtail / LaPerm / Maine Coon / Manx / Mekong bobtail / Minskin / Munchkin / Nebelung / Napoleon / 
    Norwegian Forest Cat / Ocicat / Ojos Azules / Oregon Rex / Oriental Bicolor / Oriental Shorthair / 
    Oriental Longhair / Persian / Peterbald / Pixie-bob / Ragamuffin / Ragdoll / Russian Blue / Russian Black / 
    Sam Sawet / Savannah / Scottish Fold / Selkirk Rex / Serengeti cat / Serrade petit / Siamese / Siberian / 
    Singapura / Snowshoe / Sokoke / Somali / Sphynx / Swedish forest cat / Thai / Tonkinese / Toyger / 
    Turkish Angora / Turkish Van / Ukrainian Levkoy / York Chocolate Cat''')

##############################################################################

mobile = phrases('''Mozilla/5.0 (Linux; U; Android 2.3.4; en-us; Kindle Fire HD Build/GINGERBREAD) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1
Mozilla/5.0 (Linux; U; Android 2.3.4; en-us; Kindle Fire Build/GINGERBREAD) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1
Mozilla/5.0 (iPad; CPU OS 4_3_5 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8L1 Safari/6533.18.5
Mozilla/5.0 (iPad; CPU OS 7_0 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11A465 Safari/9537.53
Mozilla/5.0 (Linux; U; Android 4.0.2; en-us; Galaxy Nexus Build/ICL53F) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30
Mozilla/5.0 (Linux; U; Android 2.3.6; en-us; Nexus S Build/GRK39F) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1
Mozilla/5.0 (BB10; Touch) AppleWebKit/537.1+ (KHTML, like Gecko) Version/10.0.0.1337 Mobile Safari/537.1+
Mozilla/5.0 (PlayBook; U; RIM Tablet OS 2.1.0; en-US) AppleWebKit/536.2+ (KHTML, like Gecko) Version/7.2.1.0 Safari/536.2+
Mozilla/5.0 (BlackBerry; U; BlackBerry 9900; en-US) AppleWebKit/534.11+ (KHTML, like Gecko) Version/7.0.0.187 Mobile Safari/534.11+
Mozilla/5.0 (Linux; Android 4.1.2; Nexus 7 Build/JZ054K) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.166 Safari/535.19
Mozilla/5.0 (Linux; Android 4.0.4; Galaxy Nexus Build/IMM76B) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.133 Mobile Safari/535.19
Mozilla/5.0 (Android; Mobile; rv:14.0) Gecko/14.0 Firefox/14.0
Mozilla/5.0 (Android; Tablet; rv:14.0) Gecko/14.0 Firefox/14.0
Mozilla/5.0 (iPad; CPU OS 7_0_2 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11A501 Safari/9537.53
Mozilla/5.0 (iPad; CPU OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5376e Safari/8536.25
Mozilla/5.0 (iPhone; CPU iPhone OS 7_0_2 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11A4449d Safari/9537.53
Mozilla/5.0 (iPhone; CPU iPhone OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5376e Safari/8536.25
Mozilla/5.0 (MeeGo; NokiaN9) AppleWebKit/534.13 (KHTML, like Gecko) NokiaBrowser/8.5.0 Mobile Safari/534.13
Mozilla/5.0 (compatible; MSIE 10.0; Windows Phone 8.0; Trident/6.0; IEMobile/10.0; ARM; Touch; NOKIA; Lumia 820)
NokiaN97/21.1.107 (SymbianOS/9.4; Series60/5.0 Mozilla/5.0; Profile/MIDP-2.1 Configuration/CLDC-1.1) AppleWebkit/525 (KHTML, like Gecko) BrowserNG/7.1.4''', "\n")

desktop = phrases('''Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Trident/6.0)
Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)
Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0)
Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.63 Safari/537.36
Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.16 Safari/537.36
Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:2.0.1) Gecko/20100101 Firefox/4.0.1
Mozilla/5.0 (Windows NT 6.1; rv:2.0.1) Gecko/20100101 Firefox/4.0.1
Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:7.0.1) Gecko/20100101 Firefox/7.0.1
Mozilla/5.0 (Windows NT 6.1; Intel Mac OS X 10.6; rv:7.0.1) Gecko/20100101 Firefox/7.0.1
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.63 Safari/537.36 OPR/18.0.1284.68
Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.63 Safari/537.36 OPR/18.0.1284.68
Opera/9.80 (Macintosh; Intel Mac OS X 10.9.1) Presto/2.12.388 Version/12.16
Opera/9.80 (Windows NT 6.1) Presto/2.12.388 Version/12.16''', "\n")

##############################################################################

ALL = [ # An example has two sets of strings, each with a one-character initial identifying it.
    (winners, 'W', 'L', losers),
    (boys, 'B', 'G', girls),
    (nfl_in, 'I', 'O', nfl_out),
    (pharma, 'P', 'C', cities),
    (foo, 'F', 'B', bar),
    (starwars, 'W', 'T', startrek),
    (nouns, 'N', 'A', adverbs),
    (nouns, 'N', 'V', verbs),
    (randoms, 'R', 'B', builtins),
    (dogs, 'D', 'C', cats)]
ALL = [
    (mobile, 'M', 'D', desktop)
]
ALL = [d for datum in ALL for d in (datum, datum[::-1])] # Add in the reverse versions

SOLUTION = {} # Remember solutions; SOLUTION[W, L] will hold a regex
               
def benchmark(data=ALL, calls=10000): 
    "Run these data sets; print summaries; return total of solution lengths."
    total = 0
    for (W, Wname, Lname, L) in data:
        re.purge()
        t0 = time.time()
        bb = bb_findregex(W, L, calls)
        t1 = time.time()
        SOLUTION[W, L] = bb.solution
        assert verify(bb.solution, W, L)
        print '{:3d} ch {:3d} win {:6.2f} s {:7,d} calls {}-{}: {!r}'.format(
            len(bb.solution), len(W), t1-t0, (calls - bb.calls), Wname, Lname, bb.solution)
        total += len(bb.solution)
    return total

##############################################################################

def test_bb():
    assert OR(['a', 'b', 'c']) == OR('a', 'b', 'c') == 'a|b|c'
    assert OR(['a|b', 'c|d']) == OR('a|b', 'c|d') == 'a|b|c|d'
    assert OR(None, 'c') == 'c'
    covers1 = {'a': {'ann', 'abe'}, 'ab': {'abe'}}
    assert eliminate_dominated(covers1) == {'a': {'ann', 'abe'}}
    assert simplify_covers(covers1) == ({}, 'a')
    covers2 = {'a': {'abe', 'cab'}, 'b': {'abe', 'cab', 'bee'}, 
               'c': {'cab', 'cee'}, 'c.': {'cab', 'cee'}, 'abe': {'abe'},
               'ab': {'abe', 'cab'}, '.*b': {'abe', 'cab', 'bee'}, 
               'e': {'abe', 'bee', 'cee'}, 'f': {}, 'g': {}}
    assert eliminate_dominated(covers2) == simplify_covers(covers2)[0] == {
        'c': {'cab', 'cee'}, 'b': {'cab', 'abe', 'bee'}, 'e': {'cee', 'abe', 'bee'}}
    covers3 = {'1': {'w1'}, '.1': {'w1'}, '2': {'w2'}}
    assert eliminate_dominated(covers3) == {'1': {'w1'}, '2': {'w2'}}
    assert simplify_covers(covers3) == ({}, '1|2')
    assert select_necessary({'a': {'abe'}, 'c': {'cee'}}) == ({}, 'a|c')
    assert {0, 1, 2} >= {1, 2}
    assert {1, 2} >= {1, 2}
    assert not ({1, 2, 4} >= {1, 3})
    assert bb_findregex(starwars, startrek).solution == ' T|P.*E'
    return 'test_bb passes'

def test_rep():
    assert repetitions('a') == {'a+', 'a*', 'a?'}
    assert repetitions('ab') == {'a+b', 'a*b', 'a?b', 
                                 'ab+', 'ab*', 'ab?'}
    assert repetitions('a.c') == {'a+.c', 'a*.c', 'a?.c',
                                  'a.c+', 'a.*c', 'a.?c',
                                  'a.+c', 'a.c*', 'a.c?'}
    assert repetitions('^a..d$') == {'^a+..d$', '^a*..d$', '^a?..d$', 
                                     '^a..d+$', '^a..d*$', '^a..d?$'}
    assert (eliminate_dominated(regex_covers(
           {'one', 'on'}, {'won', 'wuan', 'juan'}))
           == {'e': {'one'}, '^o': {'on', 'one'}})
    return 'test_rep passes'

if __name__ == '__main__':
    print test_rep()
    print test_bb()
    total = benchmark()
    print 'benchmark total', total
