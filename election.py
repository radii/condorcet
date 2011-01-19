#!/usr/bin/env python

"""This program reads ballots from a text file and runs a Condorcet election
using the Schulze method.  The text file should contain a line starting with
"Position:" that names the position, a line starting with "Candidates:" that
lists the candidates, and then ballots, one per line, where each ballot is a
space-separated list of rankings.  Each ranking can be either a number or a
hyphen to specify no ranking.  Lines starting with "#" are ignored."""

__author__ = 'Ka-Ping Yee <ping@zesty.ca>'
__date__ = '2005-03-28'

import sys, os, time, getopt

def elect(candidates, prefer):
    """Determine the winner of an election using the Schulze method (sometimes
    called CSSD).  'candidates' should be a list of candidates and 'prefer'
    should be a dictionary that maps the pair (i, j) to the number of voters
    who prefer candidate i to candidate j."""
    
    # Compute the margin of victory for each candidate i over candidate j.
    margin = {}
    n = len(candidates)
    for i in range(n):
        for j in range(n):
            margin[i, j] = prefer[i, j] - prefer[j, i]

    # Find the strength of the beatpath from j to k using the Floyd algorithm.
    for i in range(n):
        for j in range(n):
            for k in range(n):
                if i != j != k != i:
                    smallest = min(margin[j, i], margin[i, k])
                    if margin[j, k] < smallest:
                        margin[j, k] = smallest

    # Any candidate who remains unbeaten is a winner.
    winners = []
    for i in range(n):
        for j in range(n):
            if margin[j, i] > margin[i, j]:
                break
        else:
            winners.append(i)
    return winners
    
def tally(candidates, ballots):
    """Collect a list of ballots into a preference matrix.  'ballots' should
    be a list of ballots, where each ballot is a list of rankings.  For
    example, if there are 3 candidates, each ballot should be a list of 3
    numbers corresponding to the candidates.  Smaller rankings are better."""
    prefer = {}
    n = len(candidates)
    for i in range(n):
        for j in range(n):
            prefer[i, j] = 0
    for ballot in ballots:
        for i in range(n):
            for j in range(n):
                if ballot[i] < ballot[j]:
                    prefer[i, j] += 1
    return prefer

def read(file):
    """Read the position, candidates, and list of ballots from a text file."""
    lineno = 0

    # Find the lines that specify the position and the candidates.
    position = candidates = None
    for line in file:
        lineno += 1
        line = line.split('#', 1)[0].strip()
        if ':' in line:
            label, value = line.split(':', 1)
            if label.strip().lower() == 'position':
                position = value.strip()
            if label.strip().lower() == 'candidates':
                candidates = value.split()
        if position and candidates: break
    if not position:
        raise ValueError('No position was specified in the file.\n'
            'Please make sure there is a line starting with "Position:".')
    if not candidates:
        raise ValueError('No candidates were specified in the file.\n'
            'Please make sure there is a line starting with "Candidates:".')

    # Read in the ballots.
    n = len(candidates)
    ballots = []
    for line in file:
        lineno += 1
        line = line.split('#', 1)[0].strip()
        if line:
            try:
                ballot = [x == '-' and 9999 or int(x) for x in line.split()]
                assert len(ballot) == n
            except:
                raise ValueError(
'The ballot on line number %d is invalid.  It looks like this:\n\n%s\n\n'
'There are %d candidates, so each ballot should contain %d entries\n'
'separated by spaces.  Each entry must be a number or a hyphen.' % (
    lineno, line, n, n))
            ballots.append(ballot)
    return position, candidates, ballots

def run_several(position, candidates, ballots, nwinners = 1):
    """Run a multi-winner election by calling run() repeatedly,
    removing the winner on each iteration.
    """
    date = '%04d-%02d-%02d' % time.localtime()[:3]

    # Describe the main outcome.
    title = 'Election Results for %s (%s)' % (position, date)
    output = '\n# ' + title + '\n# ' + '='*len(title) + '\n# \n'
    outputbody = ''
    if nwinners > 1:
	output += '# Filling %d positions\n#\n' % nwinners
    for i in xrange(1, nwinners+1):
	if nwinners > 1:
	    posname = "%s %d" % (position, i)
	else:
	    posname = position
	(header, body, winners) = run(posname, candidates, ballots)
	output += '\n'
	output += '\n'
	output += '#\n'
	output += '# Position %d\n' % i
	output += '# %s\n' % ('-' * len('Position %d' % i))
	output += '\n'.join(header) + '\n'
	outputbody += '\n'
	outputbody += '# Position %d\n' % i
	outputbody += '\n'.join(body) + '\n'
	for winner in winners:
	    del candidates[winner]
	    for ballot in ballots:
		del ballot[winner]

    # Prepare the output file.
    filename = date + '-'
    for letter in position:
        if letter.lower() in 'abcdefghijklmnopqrstuvwxyz0123456789':
            filename += letter
        else:
            filename += '-'
    filename += '.txt'
    try:
        out = open(filename, 'w')
	print >>out, output
	print >>out, outputbody
    except IOError:
        raise IOError('The results could not be saved.  Please make sure\n'
            'your input file is in a folder where you can write new files.')
    return filename

def run(position, candidates, ballots):
    """Run an election.  Write a report to a file in the current directory."""
    n = len(candidates)
    winners = elect(candidates, tally(candidates, ballots))

    output = []

    if len(winners) > 1:
        output.append('# There is a TIE between %d winners:' % len(winners))
    for winner in winners:
        output.append('#     Winner: %s' % candidates[winner])

    # Describe how the winners defeated other candidates.
    prefer = tally(candidates, ballots)
    for i in winners:
        output.append('')
        output.append('# %s defeats:' % candidates[i])
        for j in range(n):
            pro, con = prefer[i, j], prefer[j, i]
            if pro > con:
                output.append('#     %s by %d to %d (%d%% in favour)' % (
                    candidates[j], pro, con, int(100*pro/(pro + con))))

    # Describe the other pairings between candidates.
    output.append('')
    for i in range(n):
        for j in range(n):
            if i != j and (i not in winners or i in winners and j in winners):
                pro, con = prefer[i, j], prefer[j, i]
                if pro == con and i > j:
                    output.append('# %s is tied with %s (%d to %d)' % (
                        candidates[i], candidates[j], pro, con))
                elif pro > con:
                    output.append(('# %s defeats %s by %d to %d '
                                     '(%d%% in favour)' % (
                        candidates[i], candidates[j], pro, con,
                        int(100*pro/(pro + con)))))

    # Record the ballot data.
    appendix = []
    appendix.append('\n# The following is a copy of the input used.')
    appendix.append('\nPosition: %s' % position)
    appendix.append('Candidates: %s' % ' '.join(candidates))
    appendix.append('\n# The following %d ballots were cast:' % len(ballots))
    for ballot in ballots:
        appendix.append(' '.join(
            [rank == 9999 and '-' or str(rank) for rank in ballot]))
    return (output, appendix, winners)

def main():
    nwinners = 1
    (opts, args) = getopt.getopt(sys.argv[1:], 'n:')
    for i in opts:
	if i[0] == '-n':
	    nwinners = int(i[1])
	else:
	    sys.exit(1)
    if len(args) == 1:
	infile = args[0]
	try:
	    position, candidates, ballots = read(open(infile))
	    os.chdir(os.path.dirname(infile) or '.')
	    outfile = run_several(position, candidates, ballots, nwinners)
	    print 'Election results saved to: %s' % outfile
	    if sys.platform == 'win32':
		os.startfile(outfile)
	    elif sys.platform == 'darwin':
		os.system('open "%s"' % outfile)
	    else:
		os.system('grep -i winner "%s"' % outfile)
	except Exception, error:
	    raise
	    print 'There was a problem running the election.'
	    print error
	    sys.exit(1)
    else:
	print 'Please see the instructions in the START-HERE file.'
	sys.exit(1)

if __name__ == '__main__':
    main()
