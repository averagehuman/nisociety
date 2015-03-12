
import re, string

class MultiReplace:

    def __init__(self, repl_dict):
        # "compile" replacement dictionary

        # assume char to char mapping
        charmap = map(chr, range(256))
        for k, v in repl_dict.items():
            if len(k) != 1 or len(v) != 1:
                self.charmap = None
                break
            charmap[ord(k)] = v
        else:
            self.charmap = string.join(charmap, "")
            return

        # string to string mapping; use a regular expression
        keys = repl_dict.keys()
        keys.sort() # lexical order
        keys.reverse() # use longest match first
        pattern = string.join(map(re.escape, keys), "|")
        self.pattern = re.compile(pattern)
        self.dict = repl_dict

    def replace(self, str):
        # apply replacement dictionary to string
        if self.charmap:
            return string.translate(str, self.charmap)
        def repl(match, get=self.dict.get):
            item = match.group(0)
            return get(item, item)
        return self.pattern.sub(repl, str)

daycodes = 'M T W TH F S SU'.split()
daynames = 'Monday Tuesday Wednesday Thursday Friday Saturday Sunday'.split()
daycode_to_name = dict(zip(daycodes, daynames))
replace_names = MultiReplace(dict(zip(daynames, daycodes))).replace
sdaycodes = ''.join(daycodes)
daycode_atomic_weights = [2**i for i in range(7, 0, -1)]

def xcombinations(items, n):
    if n==0:
        yield []
    else:
        for i in xrange(len(items)):
            #yield items[:i]
            for cc in xcombinations(items[i+1:],n-1):
                yield [items[i]]+cc


def idaycode_combos():
    for i in xrange(1, 8):
        for rng in xcombinations(daycodes, i):
            names = [daycode_to_name[code] for code in rng]
            id = ''.join(rng)
            # the weight gives precedence to days that are earlier in the 
            # week, so that, for a given set of disjoint time periods,
            # earlier periods can be displayed before later periods
            # eg. Monday-Friday, Saturday, Sunday
            # eg. "Monday, Wednesday, Friday" and "Tuesday, Thursday, Saturday"
            # it is up to the application to ensure that time periods for
            # any given route *are* disjoint
            weight = sum(2**(7-daycodes.index(s)) for s in rng)
            if i == 1:
                yield id, (weight, names[0])
            else:
                if len(rng) > 2 and id in sdaycodes:
                    # consecutive days, eg. Monday to Thursday
                    displayname = '%s to %s' % (names[0], names[-1])
                    # want to yield both options, eg. M-W and MTW
                    # this implies weight is not unique in resulting dataset
                    yield id, (weight, displayname)
                    yield '%s-%s' % (rng[0], rng[-1]), (weight, displayname)
                else:
                    names[-2:] = ['%s and %s' % (names[-2], names[-1])]
                    displayname = ', '.join(names)
                    yield id, (weight, displayname)

timeframe_combinations = dict(idaycode_combos())

def get_time_period_name_and_weight(s):
    """
    >>> get = get_time_period_name_and_weight
    >>> name1, weight1 = get('Monday - Friday')
    >>> name2, weight2 = get('M-F')
    >>> name3, weight3 = get('MTWTHF')
    >>> weight1 == weight2 == weight3
    True
    >>> name1 == name2 == name3
    True
    >>> name1
    'Monday to Friday'
    >>> get('WTHSU')
    ('Wednesday, Thursday and Sunday', 50)

    Days can be retrieved from weight::

    >>> assert 50 | (2**7) != 50
    >>> assert 50 | (2**6) != 50
    >>> assert 50 | (2**5) == 50 # Wednesday
    >>> assert 50 | (2**4) == 50 # Thursday
    >>> assert 50 | (2**3) != 50
    >>> assert 50 | (2**2) != 50
    >>> assert 50 | (2**1) == 50 # Sunday

    Compare weights::

    >>> weight1 = get('MWF')[1]
    >>> weight2 = get('TTHS')[1]
    >>> weight1 > weight2
    True
    >>> weight1 = get('M')[1]
    >>> weight2 = get('T-SU')[1]
    >>> weight1 > weight2
    True
    """
    weight, name = timeframe_combinations[''.join(replace_names(s).split()).upper()]
    return name, weight

def split_timeframe(tf):
    """
    >>> list(split_timeframe('M-F'))
    ['M', 'T', 'W', 'TH', 'F']
    >>> list(split_timeframe('S'))
    ['S']
    >>> list(split_timeframe('Th-Su'))
    ['TH', 'F', 'S', 'SU']
    >>> list(split_timeframe('MFS'))
    ['M', 'F', 'S']
    """
    name, weight = get_time_period_name_and_weight(tf)
    for i, (w, daycode) in enumerate(zip(daycode_atomic_weights, daycodes)):
        if weight & w:
            yield i, daycode

if __name__ == '__main__':
    import doctest
    doctest.testmod()

