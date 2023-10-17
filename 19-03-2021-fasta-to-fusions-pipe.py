import sys, csv, subprocess, os, argparse
from datetime import date
from statistics import median
from collections import Counter
import copy
# import time
# import json
import numpy

def binarySearch(arr, t):
	if t <= arr[0]: return arr[0]
	if t >= arr[-1]: return arr[-1]
	i, j, mid = 0, len(arr)-1, 0
	while i < j:
		mid = int((i + j)/2)
		if arr[mid] == t: return arr[mid]
		elif t < arr[mid]:
			if mid > 0 and t > arr[mid-1]:
				if abs(arr[mid]-t) < abs(arr[mid-1]-t): return arr[mid]
				else: return arr[mid-1]
			j = mid
		else:
			if mid < len(arr)-1 and t < arr[mid+1]:
				if abs(arr[mid]-t) < abs(arr[mid+1]-t): return arr[mid]
				else: return arr[mid+1]
			i = mid + 1

#Removing all repetitive region references

parser = argparse.ArgumentParser(description='fusion caller parse options', usage='python3 19-03-2021-flair-to-fusions-pipe.py -g genome.fa -t anno.gtf -a anno-short.gtf -f path-to-flair -r reads.fastq')
parser.add_argument('-o', '--output', action='store', dest='o', default=date.today().strftime("%d-%m-%Y"), help='output file name base (default: date)')
parser.add_argument('-r', '--reads', action='store', dest='r', default="", help='.fa or fq file')
parser.add_argument('-m', '--bedFile', action='store', dest='m', default="", help='.bed file')
parser.add_argument('-f', '--flair', action='store', dest='f', default=os.path.dirname(os.path.realpath(__file__))+"/flair/flair.py", help='flair path')
parser.add_argument('-g', '--genome', action='store', dest='g', default=os.path.dirname(os.path.realpath(__file__))+"/GRCh38.primary_assembly.genome.fa", help='path to genome')
#parser.add_argument('-x', '--minimap', action='store', dest='x', default="/private/groups/brookslab/bin/minimap2", help='path to minimap')
parser.add_argument('-k', '--remapSize', action='store', dest='k', default=0, type=int, help='size of area to remap - only remaps if this is specified')
parser.add_argument('-t', '--transcriptome', action='store', dest='t', default=os.path.dirname(os.path.realpath(__file__))+"/gencode.v37.annotation.gtf", help='path to transcriptome (.gtf)')
parser.add_argument('-n', '--spliceJunctions', action='store', dest='n', default=os.path.dirname(os.path.realpath(__file__))+"/intropolis.liftover.hg38.junctions.sorted.txt", help='path to splice junction file (.txt)')
parser.add_argument('-e', '--dupGenes', action='store', dest='e', default=os.path.dirname(os.path.realpath(__file__))+"/human_duplicated_genes.tsv", help='path to dup genes list')
parser.add_argument('-b', '--buffer', action='store', dest='b', default=50000, help='length of buffer for combining nearby regions')
parser.add_argument('-l', '--readSupport', action='store', dest='l', default=3, help='number of reads required to call fusion')
parser.add_argument('-a', '--anno', action='store', dest='a', default=os.path.dirname(os.path.realpath(__file__)) + "/gencode.v37.annotation-short.gtf", help='path to anno.gtf')
parser.add_argument('-p', '--bedProcess', action='store_true', dest='p', help='whether to take .bam and convert to .bed and process (True = assume existing processed .bam)')
parser.add_argument('-s', '--samConvert', action='store_true', dest='s', help='whether to convert .bam to .sam or (True = convert .bam (from fq prefix) to .sam)')
parser.add_argument('-y', '--includeMito', action='store_true', dest='y', help='whether to include fusions that are in the mitochondria (True=include)')
parser.add_argument('-w', '--removePromiscuous', action='store_true', dest='w', help='whether to filter out promiscuous chimeric genes')
# parser.add_argument('-q', '--geneCov', action='store_true', dest='q', help='whether to filter out fusions ')
# parser.add_argument('-v', '--fastqCov', action='store_true', dest='v', help='whether to include fusions that are in the mitochondria (True=include)')
parser.add_argument('-u', '--flairAlign', action='store_true', dest='u', help='whether to run flair align (True=already aligned, dont run)')
parser.add_argument('-c', '--flairCorrect', action='store_true', dest='c', help='whether to run flair correct (True=already corrected, dont run)')
parser.add_argument('-d', '--detectFusions', action='store_true', dest='d', help='whether to detect fusions (True=already detected, dont run)')
parser.add_argument('-i', '--callIsoforms', action='store_true', dest='i', help='whether to detect fusion isoforms (True=already detected, dont run)')
parser.add_argument('-j', '--matchFusionIsos', action='store_true', dest='j', help='whether to match isoforms to fusions (True=already matched or dont want to match, dont run)')
parser.add_argument('-z', '--cpu', dest='z', default=4, type=int, help='cpu number for alignment')
#/private/groups/brookslab/reference_annotations/
args = parser.parse_args()
prefix = '.'.join(args.r.split('.')[:-1])
print(prefix)

bedFileMade = False
if len(args.r) > 0 and not args.u and not args.p:
	process = subprocess.Popen('python3 ' + args.f + ' align -g ' + args.g + ' -t ' + str(args.z) + ' -r ' + args.r + ' -o ' + prefix + '.aligned' +  #+ ' -m ' + args.x,
								'; bamToBed -bed12 -i ' + prefix + '.aligned.bam > ' + prefix + '.aligned.bed',
								#'; rm ' + prefix + '.aligned.bam ' + prefix + '.aligned.bam.bai',
							   stdout=subprocess.PIPE, shell=True)
	print(process.communicate()[0].strip())
	bedFileMade = True

if (bedFileMade or os.path.exists(prefix + '.aligned.bed') or len(args.m) > 0) and not args.c and not args.p:
	correctQ = args.m if len(args.m) > 0 else prefix + '.aligned.bed'
	print('-------------------------------------------')
	process = subprocess.Popen('python3 ' + args.f + ' correct -g ' + args.g + ' -f ' + args.t + ' -q ' + correctQ + ' -o ' + prefix,
							   stdout=subprocess.PIPE, shell=True)
	print(process.communicate()[0].strip())
if not args.p:
	correctQ = args.m if args.c else prefix + '_all_corrected.bed'
	#'python3 ' + os.path.dirname(os.path.realpath(__file__)) + '/standardizeBed.py' + ' -i ' + correctQ,
	myCommands = ['bedtools intersect -wao -a ' + correctQ.rstrip('bed').rstrip('.') + '.bed' + ' -b ' + args.a + ' > ' + prefix + '-bedtools-genes.txt',
				  'python3 ' + os.path.dirname(os.path.realpath(__file__)) + '/bedtoolsGeneHelper.py' + ' -i ' + prefix + '-bedtools-genes.txt']
				  #'rm ' + prefix + '-bedtools-genes.txt']
	process = subprocess.Popen('; '.join(myCommands), stdout=subprocess.PIPE, shell=True)
	print(process.communicate()[0].strip())

#outfilename = '/'.join(prefix.split('/')[:-1]) + args.o + prefix.split('/')[-1]
outfilename = args.o
if not args.d:
	args.b = int(args.b)
	meta = open(outfilename + "-meta.txt", "w")
	# metadata = {"readsup":0, "map":0, "isMito":0, "isDup":0, "tooCloseBp":0, "fastqDist":0, "tooClose2":0, "ssdist":0, "chimericLoci":0, "secondFilter":0}
	metadata = []
	bed = open(prefix + '-bedtools-genes-short.bed', 'r')
	print('loading reads')
	junctions = {}
	count = 0
	readLength = {}
	last = None

	adapterReadLocs = {}
	# for line in open(prefix.split("_")[0] + "-reads-with-central-adapters-editdist-6.txt"):
	# 	line = line.rstrip().split("\t")
	# 	adapterReadLocs[line[0]] = [int(i) for i in list(set(line[1].split(",")))]

	for line in open(args.r, 'r'):
		if line[0] == '@':
			last = line.split('\t')[0].lstrip("@")
		elif line[0] == ">":
			last = line.rstrip().lstrip(">")
		else:
			readLength[last] = len(line)
	print('loading splice junctions and genes')
	for line in open(args.n, 'r'):  # "/private/groups/brookslab/cafelton/fusions-code/gencode.v37.junctions.txt", 'r'):
		count += 1
		if count % 2 > 0:
			last = line.strip()
		else:
			temp = numpy.fromstring(line.rstrip(), dtype=int, sep=",")
			# temp = json.loads('[' + line.rstrip() + ']')
			junctions[last] = temp
	print(junctions['chr1'][:10])
	# print("loading genes")
	geneLength = {}
	allGeneLoc = {}
	for line in open(args.a, 'r'):
		if line[0] != "#":
			line = line.split('\t')
			name = line[8].split('gene_name "')[1].split('"')[0]
			geneLength[name] = int(line[4])-int(line[3])
			allGeneLoc[name] = [line[0], int(line[3]), int(line[4])]
	clinicalF = []
	for line in open(os.path.dirname(os.path.realpath(__file__))+"/treehouse-clinical-fusions.txt"):
		clinicalF.append(line.strip())
	clinicalF = set(clinicalF)
	potential_chimeric = {}  # {read name: [entries]}
	print("finding potential fusions \n")
	bedLines = []
	buffer = args.b
	maxMapQ, bedLineCount, avgMapQ = 0, 0, 0
	geneInfo = {}
	c = 0
	dupGenes = {}
	for line in open(args.e, 'r'):
		line = line.split('\t')
		dupGenes[line[7]] = line[1]
	geneReads = {}
	#GET POTEINTIAL CHIMERIC (MULTIPLE MAPPING) READS FROM BED FILE
	c = 0
	for line in bed:
		if len(line) > 20:
			c += 1
			bedLineCount += 1
			line = line.rstrip().split('\t')
			bedLines.append(line)
			readname, gene  = line[3].split('--')
			if gene.split('/')[0] not in geneReads.keys():
				geneReads[gene.split('/')[0]] = []
			geneReads[gene.split('/')[0]].append(readname)
			if '/' not in gene:
				gene = gene.replace('.0', '')
				geneInfo[gene] = None
			else:
				geneLoc = gene.split('/')
				if geneLoc[0] not in geneInfo:
					geneInfo[geneLoc[0]] = geneLoc[1:] + [line[0]]
				gene = geneLoc[0]
			avgMapQ += int(line[4])
			if int(line[4]) > maxMapQ: maxMapQ = int(line[4])
			# if c < 5:
			# 	print(readname, gene)
			if readname in potential_chimeric:
				if gene in potential_chimeric[readname]:
					potential_chimeric[readname][gene].append(line)
				else:
					potential_chimeric[readname][gene] = [line]
			else:
				potential_chimeric[readname] = {gene: [line]}
	#print(potential_chimeric)
	c = 0
	# for i in geneInfo:
	# 	c += 1
	# 	if c < 10: print(i, geneInfo[i])
	fusions_found = {}  # {fused genes: count}
	fusionReads = []
	avgMapQ = avgMapQ/float(bedLineCount)
	print("filtering potential fusions \n" + str(len(potential_chimeric.keys())))
	c = 0
	for read in potential_chimeric:
		#c += 1
		#if c % 10000 == 0: print(c)
		if len(potential_chimeric[read]) == 1:
			continue
		elif len(potential_chimeric[read]) > 1:
			c += 1
			locs = list(potential_chimeric[read].keys())
			locs.sort()
			fusion_name = '--'.join(locs)
			if fusion_name not in fusions_found:
				fusions_found[fusion_name] = {'mapScore':0, 'readNames':[]}#, 'repeatScore':0}
				for loc in locs:
					fusions_found[fusion_name][loc] = {'reads':[], 'left':[], 'right':[], 'strand':[], 'chr':potential_chimeric[read][loc][0][0]}
			for loc in locs:
				fusions_found[fusion_name][loc]['reads'] += potential_chimeric[read][loc]
				for i in potential_chimeric[read][loc]:
					fusions_found[fusion_name]['mapScore'] += int(i[4])
					#fusions_found[fusion_name]['repeatScore'] += float(i[-1])
					fusions_found[fusion_name][loc]['left'].append(int(i[1]))
					fusions_found[fusion_name][loc]['right'].append(int(i[2]))
					fusions_found[fusion_name][loc]['strand'].append(i[5])
			fusions_found[fusion_name]['readNames'].append(read)
	# print('fusions',  len(fusions_found.keys()), c)
	#AGGREGATE AND SORT NON-GENIC REGIONS IN FUSIONS
	print('condensing fusions in non-genic regions')
	leftLocs, rightLocs = {}, {}
	c = 0
	for i in fusions_found:
		locs = i.split('--')
		if len(locs[0].split('-')) > 1 and locs[0][:3] == 'chr':
			chr, loc = locs[0].split('-')
			if chr not in leftLocs:
				leftLocs[chr] = []
			leftLocs[chr].append(loc)
		if len(locs[-1].split('-')) > 1 and locs[-1][:3] == 'chr':
			try:
			    assert len(locs[-1].split('-')) == 2, locs[-1]
			    chr, loc = locs[-1].split('-')
			    if chr not in rightLocs:
			    	rightLocs[chr] = []
			    rightLocs[chr].append(loc)
			except AssertionError:
			    print(locs[-1], locs)

	#JOIN CLOSE REGIONS TOGETHER AND MARK THEM FOR UPDATING
	updateValues = [[leftLocs, {}], [rightLocs, {}]]
	for k in range(2):
		for i in updateValues[k][0]:
			lastLoc = '0'
			lastKey = None
			updateValues[k][0][i].sort()
			for j in updateValues[k][0][i]:
				if int(j)-int(lastLoc) < buffer and lastKey == None:
					lastKey = '-'.join([i, lastLoc])
					updateValues[k][1]['-'.join([i, lastLoc])] = lastKey
					updateValues[k][1]['-'.join([i, j])] = lastKey
				elif float(j)-float(lastLoc) < buffer:
					updateValues[k][1]['-'.join([i, j])] = lastKey
				else:
					updateValues[k][1]['-'.join([i, j])] = '-'.join([i, str(int(j))])
					lastKey = None
				lastLoc = j

	#CONDENSE NON-GENIC FUSION REGIONS INTO FEWER FUSIONS
	new_fusions_found = {}
	for i in fusions_found:
		locs = i.split('--')
		if len(locs[0].split('-')) > 1 and locs[0][:3] == 'chr':
			locs[0] = updateValues[0][1][locs[0]]
		if len(locs[-1].split('-')) > 1 and locs[-1][:3] == 'chr':
            # patch KeyError: 'chr22-38_28785274-29006793.1'
			try:
				locs[0] = updateValues[0][1][locs[0]]
			except KeyError:
				continue

		if '--'.join(locs) not in new_fusions_found.keys():
			new_fusions_found['--'.join(locs)] = {}
			new_fusions_found['--'.join(locs)]['mapScore'] = fusions_found[i]['mapScore']
			#new_fusions_found['--'.join(locs)]['repeatScore'] = fusions_found[i]['repeatScore']
			new_fusions_found['--'.join(locs)]['readNames'] = fusions_found[i]['readNames']
			for j in range(len(locs)):
				new_fusions_found['--'.join(locs)][locs[j]] = fusions_found[i][i.split('--')[j]]
		else:
			new_fusions_found['--'.join(locs)]['mapScore'] += fusions_found[i]['mapScore']
			#new_fusions_found['--'.join(locs)]['repeatScore'] += fusions_found[i]['repeatScore']
			new_fusions_found['--'.join(locs)]['readNames'] += fusions_found[i]['readNames']
			for j in range(len(locs)):
				if locs[j] not in new_fusions_found['--'.join(locs)]:
					new_fusions_found['--'.join(locs)][locs[j]] = fusions_found[i][i.split('--')[j]]
				elif locs[j] not in ['mapScore', 'readNames', 'repeatScore']:
					for key in ['reads', 'left', 'right', 'strand']:
						new_fusions_found['--'.join(locs)][locs[j]][key] += fusions_found[i][i.split('--')[j]][key]
	print('new fusions',  len(new_fusions_found.keys()))
	# metadata["chimericLoci"] = len(new_fusions_found.keys())
	orgFusions = []
	allMatches = []
	readNames = {}
	avgQualScore = 0
	print('filtering fusions and detecting breakpoints')
	c = 0
	#print(new_fusions_found)
	for i in new_fusions_found:
		# if i in clinicalF: print(i)
		supportCount = len(new_fusions_found[i]['readNames'])
		mapScore = round((new_fusions_found[i]['mapScore']/float(supportCount * len(i.split('--'))))/maxMapQ, 3) #* len(i.split('-')))
		#repeatScore = round((new_fusions_found[i]['repeatScore']/float(supportCount * len(i.split('--')))), 3) #* len(i.split('-')))
		avgBreakpointAgg = 0
		#print(i, supportCount, mapScore)
		#if mapScore > 0.5: print(i, supportCount, mapScore)
		isDup = False
		if i.split('--')[0] in dupGenes.keys() and i.split('--')[1] in dupGenes.keys():
			if dupGenes[i.split('--')[0]] == dupGenes[i.split('--')[1]]: isDup = True
		isMito = False
		for loc in new_fusions_found[i]:
			if loc not in ['mapScore', 'readNames', 'repeatScore']:
				if new_fusions_found[i][loc]['chr'] == "chrM": isMito=True
		if supportCount < int(args.l): metadata.append([i, 'readsup', str(supportCount), new_fusions_found[i]['readNames']])#metadata["readsup"] += 1
		if not ((mapScore >= avgMapQ/float(maxMapQ) or mapScore > 0.8) and mapScore > .5): metadata.append([i, 'mapScore', str(mapScore), new_fusions_found[i]['readNames']])#metadata["map"] += 1
		if isMito: metadata.append([i, 'isMito', 'M', new_fusions_found[i]['readNames']])#metadata["isMito"] += 1
		if isDup: metadata.append([i, 'isDup', 'D', new_fusions_found[i]['readNames']])#metadata["isDup"] += 1
		if (supportCount >= int(args.l) and (mapScore >= avgMapQ/float(maxMapQ) or mapScore > 0.8) and mapScore > .5\
				and (args.y or ('chrM' not in i and not isMito)) and not isDup) or i in clinicalF:
			currFusion = [i, str(supportCount), str(mapScore)]#, str(repeatScore)]
			distTo5 = []
			locInfo = {}
			dupLocusFrac = []
			for loc in new_fusions_found[i]:
				if loc not in ['mapScore', 'readNames', 'repeatScore']:
					leftMed, rightMed = int(median(new_fusions_found[i][loc]['left'])), int(median(new_fusions_found[i][loc]['right']))
					locInfo[loc] = {'chr':new_fusions_found[i][loc]['chr'].strip('chr'), 'loc':leftMed, 'seq':'NNNNNNNNNNNNNNNNNNNN', 'cseq':'--------------------'}
					leftFracClose, rightFracClose = 0, 0
					for j in new_fusions_found[i][loc]['left']:
						if abs(j-leftMed) <= 10: leftFracClose += 1
					for j in new_fusions_found[i][loc]['right']:
						if abs(j-rightMed) <= 10: rightFracClose += 1
					leftFracClose = leftFracClose/float(supportCount)
					rightFracClose = rightFracClose/float(supportCount)
					#print(i, loc, leftFracClose, rightFracClose)
					if geneInfo[loc] != None:
						geneStart = int(geneInfo[loc][1]) if geneInfo[loc][0] == '+' else int(geneInfo[loc][2])
					else: geneStart=None
					#s = 'm' if Counter(new_fusions_found[i][loc]['strand']).most_common(1)[0][0] == '-' else 'p'
					if loc in geneReads.keys():
						dupLocusFrac.append(round(float(len([a for a in set(geneReads[loc]) if a in new_fusions_found[i]['readNames']])) / len(geneReads[loc]), 3))
					else:
						dupLocusFrac.append('/')
					if leftFracClose > rightFracClose:
						currFusion.append(loc + '-' + new_fusions_found[i][loc]['chr'] + '-' + str(leftMed) + '-' + str(dupLocusFrac[-1]))
						avgBreakpointAgg += leftFracClose
						locInfo[loc]['side'] = 'l'
						if geneStart: distTo5.append(abs(geneStart-rightMed))
						else: distTo5.append(None)
					else:
						currFusion.append(loc + '-' + new_fusions_found[i][loc]['chr'] + '-' + str(rightMed) + '-' + str(dupLocusFrac[-1]))
						avgBreakpointAgg += rightFracClose
						locInfo[loc]['side'] = 'r'
						if geneStart: distTo5.append(abs(geneStart-leftMed))
						else: distTo5.append(None)
			if all(isinstance(x, float) for x in dupLocusFrac):
				currFusion.insert(3, str(round(sum(dupLocusFrac)/len(dupLocusFrac), 3)))
			else: currFusion.insert(3, '/')
			avgBreakpointAgg = avgBreakpointAgg/float(len(new_fusions_found[i].keys()))
			currFusion.append(mapScore*supportCount*avgBreakpointAgg)#*(1-repeatScore))
			avgQualScore += mapScore*supportCount*avgBreakpointAgg#*(1-repeatScore)
			if None not in distTo5:
				#print(distTo5)
				if distTo5[0] < distTo5[1]:
					temp = currFusion[4]
					currFusion[4] = "3'-" + currFusion[5]
					currFusion[5] = "5'-" + temp
				else:
					currFusion[4] = "3'-" + currFusion[4]
					currFusion[5] = "5'-" + currFusion[5]
					currFusion[-1] *= -1
			# print(isinstance(currFusion[4], list), currFusion[4])
			if isinstance(currFusion[4], str) and isinstance(currFusion[5], str):
				# print(currFusion[0])
				if currFusion[0].split('--')[0][:3] == 'chr':
					gene1loc = currFusion[0].split('--')[0].split('-')
					gene1loc[1] = int(gene1loc[1])
					gene1loc.append(gene1loc[1] + args.b)
				elif currFusion[0].split('--')[0] not in allGeneLoc: gene1loc = ['chrN', 0]
				else: gene1loc = allGeneLoc[currFusion[0].split('--')[0]]
				if currFusion[0].split('--')[1][:3] == 'chr':
					gene2loc = currFusion[0].split('--')[1].split('-')
					gene2loc[1] = int(gene1loc[1])
					gene2loc.append(gene2loc[1] + args.b)
				elif currFusion[0].split('--')[1] not in allGeneLoc: gene2loc = ['chrN', 0]
				else: gene2loc = allGeneLoc[currFusion[0].split('--')[1]]
				if gene1loc[1] > gene2loc[1]:
                                        temp = gene1loc.copy()
                                        gene1loc = gene2loc
                                        gene2loc = temp
				if (currFusion[4].split('-')[-3] != currFusion[5].split('-')[-3] or abs(int(currFusion[4].split('-')[-2]) - int(currFusion[5].split('-')[-2])) > args.b or i in clinicalF) and (gene1loc[0]!=gene2loc[0] or gene2loc[1]-gene1loc[2]>0):
					# print(currFusion[0])
					for j in new_fusions_found[i]['readNames']:
						readNames[j] = {'fusion': i, **copy.deepcopy(locInfo)}
					allMatches += new_fusions_found[i]['readNames']
					orgFusions.append(currFusion)
				else: metadata.append([i, 'tooClose', 'tc', new_fusions_found[i]['readNames']])#metadata["tooCloseBp"] += 1
			else: metadata.append([i, 'tooClose', 'tc', new_fusions_found[i]['readNames']])#metadata["tooCloseBp"] += 1
	# print('org fusions', len(orgFusions))
	# for i in orgFusions: print(i)
	print('-----------test bam---------------')
	os.system("ls")
	print(prefix)
	correctQ = prefix if os.path.exists(prefix + '.bam') else prefix + '.aligned'
	if args.s:
		print('identifying breakpoint sequence - making sam file')
		process = subprocess.Popen('samtools view -h -o ' + correctQ + '.sam ' + correctQ + '.bam',stdout=subprocess.PIPE, shell=True)
		print(process.communicate()[0].strip())
	correctQ = prefix if os.path.exists(prefix + '.sam') else prefix + '.aligned'
	sam = open(correctQ + '.sam', 'r')
	myReads = set(readNames.keys())
	print('identifying breakpoint sequence - searching sam file')
	for line in sam:
		line = line.rstrip().split('\t')
		if line[0] in myReads:
			finalKey = None
			for key in readNames[line[0]].keys():
				if key != 'fusion':
					if readNames[line[0]][key]['chr'] == line[2].strip('chr'):
						if finalKey == None: finalKey = key
						elif abs(readNames[line[0]][key]['loc'] - int(line[3])) < \
							abs(readNames[line[0]][finalKey]['loc'] - int(line[3])): finalKey = key
			#if len(line[9]) == 1:print('short', line[9])
			if finalKey == None: continue
			cigar, thisSeq = line[5], line[9]
			currString = ""
			if len(thisSeq) >= 20 and len(cigar) >= 2:
				if readNames[line[0]][finalKey]['side'] == 'l':
					while len(currString) < 20 and len(cigar) >= 2:
						i = 0
						while cigar[i] not in ['M', 'D', 'I', 'S', 'H', 'X', 'P', 'N']:
							i += 1
						if cigar[i] in ['M', 'I', 'X', 'S']:
							if cigar[i] == 'M' or cigar[i] == 'X':
								currString += thisSeq[:int(cigar[:i])]
							thisSeq = thisSeq[int(cigar[:i]):]
						if cigar[i] == 'D' or cigar[i] == 'N':
							currString += '-' * int(cigar[:i])
						cigar = cigar[i+1:]
					currString = currString[:20]
					readNames[line[0]][finalKey]['seq'] = line[9][:20]
				elif readNames[line[0]][finalKey]['side'] == 'r':
					while len(currString) < 20 and len(cigar) >= 2:
						i = -1
						temp = cigar.rstrip('MDISHXPN')
						while abs(i) < len(temp) and temp[i] not in ['M', 'D', 'I', 'S', 'H', 'X', 'P', 'N']:
							i -= 1
						if cigar[-1] in ['M', 'I', 'X', 'S']:
							if cigar[-1] == 'M' or cigar[-1] == 'X':
								currString = thisSeq[(-1*int(temp[i+1:])):] + currString
							thisSeq = thisSeq[:(-1*int(temp[i+1:]))]
						if cigar[-1] == 'D' or cigar[-1] == 'N':
							currString = '-' * int(temp[i+1:]) + currString
						cigar = cigar[:i]
					currString = currString[-20:]
					readNames[line[0]][finalKey]['seq'] = line[9][-20:]
				readNames[line[0]][finalKey]['cseq'] = currString
			#if line[0] in names: print(readNames[line[0]])
	sam.close()
	#for i in readNames: print(i, readNames[i])
	fusionNameFlip = []
	for i in range(len(orgFusions)):
		locScores = []
		for loc in orgFusions[i][0].split('--'):
			endSeq = [{'A':0,'C':0,'G':0,'T':0,'N':0, '*':0, '-':0} for x in range(20)]
			for read in new_fusions_found[orgFusions[i][0]]['readNames']:
				thisSeq = readNames[read][loc]['cseq']
				if len(thisSeq)==20:
					for j in range(20):
						endSeq[j][thisSeq[j]] += 1
			if len(thisSeq)==20:
				seqCalc = []
				for j in range(20):
					thisTot, thisMax = 0, 0
					for k in ['A', 'C', 'G', 'T', 'N', '*', '-']:
						thisTot += endSeq[j][k]
						if endSeq[j][k] > thisMax and k != 'N' and k != '*': thisMax = endSeq[j][k]
					seqCalc.append(float(thisMax)/thisTot)
				locScores.append(sum(seqCalc)/len(seqCalc))
			else:
				locScores.append(0)
		orgFusions[i].insert(3, str(round(sum(locScores)/len(locScores), 3)))
		if orgFusions[i][-1] < 0:
			fusionNameFlip.append(orgFusions[i][0])
			orgFusions[i][0] = '--'.join(orgFusions[i][0].split('--')[::-1])

	#second/better pass through sam
	allMatches = set(allMatches)
	readLength = {}
	# fq = open(args.r, 'r')
	# c = 0
	# #THIS NEEDS EDITING - FASTQ FILES CAN BE DIFFERENT
	# for line in fq:
	# 	c += 1
	# 	line = line.rstrip().split()
	# 	# if c < 10:
	# 	# 	print(line[0].lstrip('@'))
	# 	if line[0].lstrip('@') in allMatches:
	# 		readLength[line[0].lstrip('@')] = int(line[2].split('=')[1])
	# fq.close()
	sam = open(correctQ + '.sam', 'r')
	#myReads = set(readNames.keys())
	print('checking multi-mapping distance - searching sam file')
	readSams = {i:{'dist':[],'len':[]} for i in allMatches}
	c = 0
	allLenDiff = 0
	for line in sam:
		line = line.rstrip().split('\t')
		if line[0] in allMatches:
			c += 1
			locs = []
			i = 0
			while line[5][i] not in ['M', 'D', 'I', 'S', 'H', 'X', 'P', 'N']:
				i += 1
			if line[5][i] == 'M': locs.append(0)
			else: locs.append(int(line[5][:i]))
			i = -2
			while line[5][i] not in ['M', 'D', 'I', 'S', 'H', 'X', 'P', 'N']:
				i -= 1
			#TEMPORARY - ASSUMPTIONS
			if line[0] not in readLength:
				readLength[line[0]] = len(line[9])
			#DONE
			if line[5][-1] == 'M': locs.append(readLength[line[0]])
			else: locs.append(readLength[line[0]] - int(line[5][i+1:-1]))
			#New 10/2021
			i = 0
			last = 0
			total = 0
			while i < len(line[5]):
				if not line[5][i].isnumeric():
					if  line[5][i] not in ['S', 'H', 'I', 'P']:
						# print(last, i, myS[last], myS[i])
						total += int(line[5][last:i])
					last = i + 1
				i += 1
			fusInfo = readNames[line[0]]
			currDist = 1000000000000000000000
			currGene = None
			for loc in fusInfo.keys():
				if loc != 'fusion':
					if 'chr' + fusInfo[loc]['chr'] == line[2]:
						temp = abs(fusInfo[loc]['loc'] - int(line[3]))
						if temp < currDist:
							currGene = loc
							currDist = temp
			lenDiff=1
			if currGene != None:
				if currGene[:3] != 'chr' and currGene in geneLength:
					lenDiff = total/geneLength[currGene]
			allLenDiff += lenDiff
			#DONE
			# if c < 3:
			# 	print(line[0], readNames[line[0]])
			# c += 1
			if line[1] == '16' or line[1] == '2064':
				locs[0] = readLength[line[0]]-locs[0]
				locs[1] = readLength[line[0]] - locs[1]
				locs = locs[::-1]
			locs.append(line[2] + '-' + line[3])
			#readSams[line[0]].append(line)
			readSams[line[0]]['dist'].append(locs)
			readSams[line[0]]['len'].append(lenDiff)
			#readSams[line[0]]['fastqlen'].append(total)
	sam.close()
	# print("avg len diff", allLenDiff/c)
	#tempOut = open("readsToOverlap-2.txt", 'w')
	# tempout1 = open("drr-noOverlap.txt", 'w')
	# tempout2 = open("drr-Overlap.txt", 'w')
	c = 0
	fastqFusionLocs = {}#{i[0]:[] for i in orgFusions}
	# fusionLenDiff = {}
	# fusionFastqCov = {}
	keysToRemove = []

	# adapterOut = open(prefix.split("_")[0] + '-with-adapters-near-breakpoints-editdist-6.txt', 'w')
	for i in readSams:
		c += 1
		if len(readSams[i]['dist']) == 2:
			readSams[i]['dist'].sort()
			readSams[i]['dist'].append(readSams[i]['dist'][1][0]-readSams[i]['dist'][0][1])
			# for j in
			# if c < 10: #or i == "DRR059313.9578":
			# 	print(i, readSams[i], readNames[i]['fusion'])
			# 	print(readLength[i], readLength[i]-((readSams[i]['dist'][1][1]-readSams[i]['dist'][0][0])-(readSams[i]['dist'][1][0]-readSams[i]['dist'][0][1])))
			if readNames[i]['fusion'] not in fastqFusionLocs:
				fastqFusionLocs[readNames[i]['fusion']] = {'loc':[], 'len':[], 'fastqCov':[]}
			# if i in adapterReadLocs:
			# 	for j in adapterReadLocs[i]:
			# 		if abs(readSams[i]['dist'][0][1] - j) < 50 or abs(readSams[i]['dist'][1][0] - j) < 50:
			# 			adapterOut.write(readNames[i]['fusion'] + '\t' + i + '\t' + str(j) + '\n')
			# if readNames[i]['fusion'] not in fusionLenDiff:
			# 	fusionLenDiff[readNames[i]['fusion']] = []
			fastqFusionLocs[readNames[i]['fusion']]['loc'].append(readSams[i]['dist'])
			tempavg = sum(readSams[i]['len'])/float(len(readSams[i]['len']))
			# if readNames[i]['fusion'] == 'BCL11B--CD48' or readNames[i]['fusion'] == 'CD48--BCL11B' or readNames[i]['fusion'] == 'TCF19--MEP1A' or readNames[i]['fusion'] == 'MEP1A--TCF19':
			# 	print(readNames[i]['fusion'], readSams[i]['dist'])
			fastqFusionLocs[readNames[i]['fusion']]['len'].append(tempavg + ((max(readSams[i]['len'])-tempavg)/2))#sum(readSams[i]['len'])/float(len(readSams[i]['len'])))
			fastqFusionLocs[readNames[i]['fusion']]['fastqCov'].append(((readSams[i]['dist'][1][1]-readSams[i]['dist'][0][0])-(readSams[i]['dist'][1][0]-readSams[i]['dist'][0][1]))/readLength[i])
			#tempOut.write(readNames[i]['fusion']+ '\t' + i + '\t' + str(readSams[i]) + '\n')
			# if readNames[i]['fusion'] == 'EFHD1--UBR3' or readNames[i]['fusion'] == 'UBR3--EFHD1':
			# if readSams[i][-1] > -5: tempout1.write(i + '\n')
			# else: tempout2.write(i + '\n')
		#THIS IS TEMPORARY< REMOVE FOR MORE FLEXIBILITY/3-GENE
		else: keysToRemove.append(i)
		#DONE
	# adapterOut.close()
			# else: readSams[i].append(readSams[i][0][0]-readSams[i][1][1])
	# for i in fastqFusionLocs["CCDC6--RET"]:
	# 	print(i)
	#for i in keysToRemove: readSams.pop(i)
	for i in fastqFusionLocs:
		temp = [a[-1] for a in fastqFusionLocs[i]['loc']]
		temp.sort()
		# print(i, temp, temp[int(len(temp) / 2)])
		# print(i, fastqFusionLocs[i]['dist'])
		fastqFusionLocs[i]['loc'].append(temp[int(len(temp) / 2)])
		# print(temp[int(len(temp)/2)], int(sum(temp)/len(temp)))
		#print(temp[int(len(temp)/4):-int(len(temp)/4)])
		# print(temp)
	# print(fusionLenDiff)


	# print('fusions filtered')
	reads = open(outfilename + "Reads.bed", "w")
	fusions = open(outfilename + "Fusions.tsv", "w")
	if len(orgFusions) > 0:
		avgQualScore = avgQualScore/len(orgFusions)
	orgFusions.sort(key=lambda x:abs(x[-1]), reverse=True)
	fusions.write("#name\tspanning reads\tmapping score(1 is good)\tseq agreement near breakpoint (1 is good)\tavg frac of reads at loci in fusion\t3' breakpoint\t5' breakpoint\n")
	fusionReadLocs = {}
	orgFusionsDict = {}
	for i in orgFusions:
		#print(i)
		if abs(i[-1]) > avgQualScore*.01:
			# fusions.write('\t'.join(i[:-1]) + '\n')
			orgFusionsDict[i[0]] = i[:-1]
			fusionReadLocs[i[0]] = {i[0].split('--')[0] + '-' + i[6].split('-')[-3]:[], i[0].split('--')[1] + '-' + i[5].split('-')[-3]:[]}
	#print(avgQualScore, avgMapQ/float(maxMapQ))
	# printNames = open(outfilename + "readNames.txt", "w")
	# for readName in allMatches:
	# 	printNames.write(readName + '\n')
	# printNames.close()
	# for i in fusionReadLocs: print(fusionReadLocs[i])

	# fusions.close()
	count = 0
	last = ""
	print("num pre final filter", len(fusionReadLocs.keys()))
	# metadata["secondFilter"] = len(fusionReadLocs.keys())
	bedLinesFiltered = []
	fusionDist = {a:[] for a in list(fusionReadLocs.keys())}
	for line in bedLines:
		thisName = line[3].split('--')[0]
		if thisName in allMatches:
			if readNames[thisName]['fusion'] in fusionNameFlip:fName = '--'.join(readNames[thisName]['fusion'].split('--')[::-1])
			else: fName = readNames[thisName]['fusion']
			currName = line[3].split('--')[1].split('/')[0]
			if currName[:3] == 'chr':
				#currName = currName.split('.')[0]
				for loc in readNames[thisName]:
					if loc[:3] == 'chr':
						if abs(float(currName.split('-')[1]) - float(loc.split('-')[1])) <= args.b * 3:
							currName = loc
			locName = line[3].split('--')[1].split('/')[0] if '-' not in line[3].split('--')[1].split('/')[0] else line[3].split('--')[1].split('/')[0].split('.')[0]
			if fName in fusionReadLocs:
				if locName + '-' + line[0] in fusionReadLocs[fName]:
					fusionReadLocs[fName][locName + '-' + line[0]].append([int(line[1]), int(line[2])])
			if currName in readNames[thisName].keys():
				thisSeq = readNames[thisName][currName]['cseq']
				line[3] = '-.-'.join([fName] + line[3].split('--') + [thisSeq])
				if line[-2][-1] != ',':
					line[-2] += ','
					line[-1] += ','
				bedLinesFiltered.append(line)
	c = 0
	x = 0
	finalFusions = []
	almostDone = []
	adGenes = []
	for fusion in fusionReadLocs:
		wasWritten = False
		theseLocs = []
		SSdist = []
		readEnds = []
		counts = []
		chrs = []
		for loc in fusionReadLocs[fusion]:
			chrs.append(loc.split('-')[-1])
			temp = [list(i) for i in zip(*fusionReadLocs[fusion][loc])]
			# if c > 7:
			# 	print(fusion, loc, fusionReadLocs[fusion][loc])
			# 	print(temp)
			# 	print(fusionReadLocs[fusion][loc][0])
			#fusionReadLocs[fusion][loc] = [list(i) for i in zip(*fusionReadLocs[fusion][loc])]
			#print(temp)
			# if fusion == "TRIM37--RPS6KB1":
			# 	print(sorted(temp[0]))
			# 	print(sorted(temp[1]))
			far = True
			if len(temp) > 0:
				temp[0].sort()
				temp[1].sort()
				counts.append(min(temp[0]))
				counts.append(max(temp[1]))
				leftSS1 = binarySearch(junctions[loc.split('-')[-1]], temp[0][int(len(temp[0])/2)])
				rightSS1 = binarySearch(junctions[loc.split('-')[-1]], temp[1][int(len(temp[1]) / 2)])
				#leftSS1 = min(junctions[loc.split('-')[-1]], key=lambda x:abs(x-temp[0][int(len(temp[0])/2)]))
				#rightSS1 = min(junctions[loc.split('-')[-1]], key=lambda x: abs(x - temp[1][int(len(temp[1]) / 2)]))
				if len(temp[0]) % 2 == 0 and len(temp) > 2:
					#leftSS2 = min(junctions[loc.split('-')[-1]],key=lambda x: abs(x - temp[0][int(len(temp[0]) / 2)+1]))
					#rightSS2 = min(junctions[loc.split('-')[-1]],key=lambda x: abs(x - temp[1][int(len(temp[1]) / 2)+1]))
					leftSS1 = binarySearch(junctions[loc.split('-')[-1]], temp[0][int(len(temp[0]) / 2)]+1)
					rightSS1 = binarySearch(junctions[loc.split('-')[-1]], temp[1][int(len(temp[1]) / 2)]+1)
					leftDistToSS = min([abs(leftSS1-temp[0][int(len(temp[0])/2)]), abs(leftSS2-temp[0][int(len(temp[0])/2)+1])])
					rightDistToSS = min([abs(rightSS1 - temp[1][int(len(temp[1]) / 2)]), abs(rightSS2 - temp[1][int(len(temp[1]) / 2) + 1])])
				else:
					leftDistToSS = abs(leftSS1-temp[0][int(len(temp[0])/2)])
					rightDistToSS = abs(rightSS1-temp[1][int(len(temp[1])/2)])
				SSdist.append(sorted([[leftDistToSS, temp[0][int(len(temp[0])/2)]], [rightDistToSS,temp[1][int(len(temp[1])/2)]]]))
				#readEnds.append([temp[0][int(len(temp[0])/2)], temp[1][int(len(temp[1])/2)]])
				theseLocs.append(loc.split('-')[0])
				# print(SSdist[-1])
				#print(fusion, loc, temp[0][int(len(temp[0])/2)], leftDistToSS, temp[1][int(len(temp[1])/2)], rightDistToSS)#, temp[int(len(temp)/4):-int(len(temp)/4)])
			else: far = False
		# print(f, fusions[f], counts)
		#print(counts)
		if len(counts) > 2:
			if abs(counts[0] - counts[2]) < args.b or abs(counts[0] - counts[3]) < args.b or \
					abs(counts[1] - counts[2]) < args.b or abs(counts[1] - counts[3]) < args.b:
				far = False
		fastqDist = 500
		lenDiff = 0
		if fusion in fastqFusionLocs:
			fastqDist = abs(fastqFusionLocs[fusion]['loc'][-1])
			lenDiff = str(sum(fastqFusionLocs[fusion]['len']) / len(fastqFusionLocs[fusion]['len']))
			fastqCov = str(sum(fastqFusionLocs[fusion]['fastqCov']) / len(fastqFusionLocs[fusion]['fastqCov']))
		elif '--'.join(fusion.split('--')[::-1]) in fastqFusionLocs:
			fastqDist = abs(fastqFusionLocs['--'.join(fusion.split('--')[::-1])]['loc'][-1])
			lenDiff = str(sum(fastqFusionLocs['--'.join(fusion.split('--')[::-1])]['len']) / len(fastqFusionLocs['--'.join(fusion.split('--')[::-1])]['len']))
			fastqCov = str(sum(fastqFusionLocs['--'.join(fusion.split('--')[::-1])]['fastqCov']) / len(fastqFusionLocs['--'.join(fusion.split('--')[::-1])]['fastqCov']))
		# print(fusion, fastqDist, far)
		fusion2 = fusion if fusion in new_fusions_found else '--'.join(fusion.split('--')[::-1])
		if fastqDist >= 15: metadata.append([fusion, 'fastqDist', str(fastqDist), new_fusions_found[fusion2]['readNames']])#metadata["fastqDist"] += 1
		if not (len(list(set(chrs))) > 1 or far): metadata.append([fusion, 'tooClose2', 'tc2', new_fusions_found[fusion2]['readNames']])#metadata["tooClose2"] += 1
		if (fastqDist < 15 and (len(list(set(chrs))) > 1 or far)) or fusion in clinicalF:
			# print(fusion, fastqDist, (far or len(list(set(chrs))) > 1))
			if len(SSdist) > 1:
				# print(SSdist[0][0][0], SSdist[1][0][0])
				#print(fusion, SSdist,SSdist[0][0][0] < 5 and SSdist[1][0][0] < 5, fastqDist)
				if SSdist[0][0][0] <= 10 and SSdist[1][0][0] <= 10:#min([a[0] for a in SSdist[0]]) < 5 and min([a[0] for a in SSdist[1]]) < 5:
					if theseLocs[0] in geneInfo:
						if geneInfo[theseLocs[0]] != None:
							aDistToProm = abs(SSdist[0][1][1] - int(geneInfo[theseLocs[0]][1])) if geneInfo[theseLocs[0]][0] == '+' else abs(SSdist[0][1][1] - int(geneInfo[theseLocs[0]][2]))
						else:
							aDistToProm = 1000000000000000
					else: aDistToProm = 1000000000000000
					if theseLocs[1] in geneInfo:
						if geneInfo[theseLocs[1]] != None:
							bDistToProm = abs(SSdist[1][1][1] - int(geneInfo[theseLocs[1]][1])) if geneInfo[theseLocs[1]][0] == '+' else abs(SSdist[0][1][1] - int(geneInfo[theseLocs[1]][2]))
						else:
							bDistToProm = 1000000000000000
					else: bDistToProm = 1000000000000000
					temp = [a.split('-') for a in list(orgFusionsDict[fusion][-2:])]
					if temp[0][-4] == theseLocs[0]:
						temp[0][-2] = str(SSdist[0][0][1])
						temp[1][-2] = str(SSdist[1][0][1])
					elif temp[1][-4] == theseLocs[0]:
						temp[0][-2] = str(SSdist[1][0][1])
						temp[1][-2] = str(SSdist[0][0][1])
					orgFusionsDict[-2] = '-'.join(temp[0])
					orgFusionsDict[-1] = '-'.join(temp[1])
					# print(theseLocs[0], aDistToProm, theseLocs[1], bDistToProm)
					# if aDistToProm < bDistToProm:
					# 	orgFusionsDict[0] = theseLocs[0] + '-' + theseLocs[1]
					# 	orgFusionsDict[-2] = "3'-" + theseLocs[1] + '-' + geneInfo[theseLocs[1]][-1] + '-' + str(SSdist[1][1][1]) + '-' + temp[0][-1]
					# 	orgFusionsDict[-1] = "5'-" + theseLocs[0] + '-' + geneInfo[theseLocs[0]][-1] + '-' + str(SSdist[0][1][1]) + '-' + temp[1][-1]
					# else:
					# 	orgFusionsDict[0] = theseLocs[1] + '-' + theseLocs[0]
					# 	orgFusionsDict[-1] = "5'-" + theseLocs[1] + '-' + geneInfo[theseLocs[1]][-1] + '-' + str(SSdist[1][1][1]) + '-' + temp[0][-1]
					# 	orgFusionsDict[-2] = "3'-" + theseLocs[0] + '-' + geneInfo[theseLocs[0]][-1] + '-' + str(SSdist[0][1][1]) + '-' + temp[1][-1]
					orgFusionsDict[fusion].append(lenDiff)
					orgFusionsDict[fusion].append(fastqCov)
					almostDone.append(orgFusionsDict[fusion])
					adGenes.append(fusion.split('--')[0])
					adGenes.append(fusion.split('--')[1])
					# fusions.write('\t'.join(orgFusionsDict[fusion]) + '\n')
					# wasWritten = True
					# finalFusions.append(fusion)
					c += 1
				else: metadata.append([fusion, 'ssDist', '-'.join([str(x) for x in SSdist]), new_fusions_found[fusion2]['readNames']])#metadata["ssdist"] += 1
			elif len(SSdist) == 1:
				if SSdist[0][0][0] < 10:
					c += 1
					almostDone.append(orgFusionsDict[fusion])
					adGenes.append(fusion.split('--')[0])
					adGenes.append(fusion.split('--')[1])
					# fusions.write('\t'.join(orgFusionsDict[fusion]) + '\n')
					# wasWritten = True
					# finalFusions.append(fusion)
				else: metadata.append([fusion, 'ssDist', '-'.join([str(x) for x in SSdist]), new_fusions_found[fusion2]['readNames']])#metadata["ssdist"] += 1
			else: metadata.append([fusion, 'ssDist', '-'.join([str(x) for x in SSdist]), new_fusions_found[fusion2]['readNames']])#metadata["ssdist"] += 1
		# if wasWritten: metadata["secondFilter"] -= 1
		# if not wasWritten: print('bad', fusion)
	c = 0
	freq = Counter(adGenes)
	for temp in almostDone:#"01-11-2021nor1_v2.3.5_passFusions.tsv"):
		good = True
		a = temp[5].split("-")
		b = temp[6].split("-")
		fusion2 = temp[0] if temp[0] in new_fusions_found else '--'.join(temp[0].split('--')[::-1])
		if len(temp) > 8 and temp[0] not in clinicalF:
			# if a[-3] != b[-3] or abs(int(a[-2])-int(b[-2])) < 1000000:
			# 	good = False
			# 	metadata.append([temp[0], 'tooClose', new_fusions_found[fusion2]['readNames']])
			if float(temp[-1]) < 0.7:
				good = False
				metadata.append([temp[0], 'fastqCov', str(temp[-1]), new_fusions_found[fusion2]['readNames']])
			if float(temp[-2]) > 0.9:
				good = False
				metadata.append([temp[0], 'geneCov', str(temp[-2]), new_fusions_found[fusion2]['readNames']])
			if args.w:
				if freq[temp[0].split("--")[0]] > 2 or freq[temp[0].split("--")[1]] > 2:
					good = False
					metadata.append([temp[0], 'repeat', 'r', new_fusions_found[fusion2]['readNames']])
		# else: good=False
		# else: print(temp[0], freq[temp[0].split("--")[0]], freq[temp[0].split("--")[1]])
		if good:
			finalFusions.append(temp[0])
			fusions.write('\t'.join(temp[:7]) + '\n')
			c += 1
	print("final output", c)
	fusions.close()
	print('fusions written')
	for i in metadata:
		i[3] = ','.join(i[3])
		meta.write('\t'.join(i) + '\n')#i + "\t" + str(metadata[i]) + "\n")
	meta.close()
	#print(finalFusions[:3])
	#print(len(finalFusions))
	finalFusions = set(finalFusions)
	#print(len(bedLinesFiltered))
	#print(bedLinesFiltered[:3])
	printNames = open(outfilename + "readNames.txt", "w")
	for line in bedLinesFiltered:
		if line[3].split('-.-')[0] in finalFusions:
			reads.write("\t".join(line) + "\n")
			printNames.write(line[3].split('-.-')[1] + '\n')

	reads.close()
	printNames.close()
	print('reads written')
	# subprocess.run(['perl', os.path.dirname(os.path.realpath(__file__)) + '/bed12ToGTF.pl'],
	# 			   stdin=open(args.o + prefix + 'Reads.bed', 'r'), stdout=open(args.o + prefix + 'Reads.gtf', 'w'))
if int(args.k) > 0:
	readNames = []
	print('remapping reads to fusions')
	with open(outfilename + "readNames.txt", 'r') as names:
		for line in names:
			readNames.append(line.rstrip())
	readNames = set(readNames)
	#Filter reads to only the double mapped reads
	leadingChar = '@' if args.r.split('.')[-1] == 'fastq' or args.r.split('.')[-1] == 'fq' else '>'
	with open(args.r, 'r') as reads, open(outfilename + "Filtered.fa", "w") as faOut:
		writeRead = False
		c, d = 0, 0
		for line in reads:
			c += 1
			if c % 20000000 == 0: print(c, d)
			if line[0] == leadingChar:
				if line.rstrip('\n').lstrip(leadingChar) in readNames:
					writeRead = True
					d += 1
					if leadingChar == '@': faOut.write(">" + line.lstrip('@'))
					else: faOut.write(line)
				else:
					writeRead = False
			elif writeRead:
				faOut.write(line)
				writeRead = False
	print('reads filtered')
	fusions = {}
	firstLine = []
	with open(outfilename + "Fusions.tsv", 'r') as thesefusions, open(outfilename + 'Locs.bed', 'w') as bedFile:
		for line in thesefusions:
			line = line.rstrip().split('\t')
			if line[0][0] != '#' and len(line) > 6:
				chr1, center1 = line[5].split('-')[-3:-1]
				chr2, center2 = line[6].split('-')[-3:-1]
				if int(center1) > args.k and int(center2) > args.k:
					name1 = line[0] + '->' + '-'.join(line[5].lstrip("3'-").split('-')[:-2])
					name2 = line[0] + '->' + '-'.join(line[6].lstrip("5'-").split('-')[:-2])
					fusions[line[0]] = {'line':line}
					fusions[line[0]]['-'.join(line[5].lstrip("3'-").split('-')[:-2])] = {'side':"3'", 'chr':chr1, 'bp':int(center1), 'left':[], 'right':[], 'reads':[], 'mapQ':[]}
					fusions[line[0]]['-'.join(line[6].lstrip("5'-").split('-')[:-2])] = {'side':"5'", 'chr':chr2, 'bp':int(center2), 'left':[], 'right':[], 'reads':[], 'mapQ':[]}
					bedFile.write('\t'.join([chr1, str(int(center1)-args.k), str(int(center1) + args.k), name1]) + '\n')
					bedFile.write('\t'.join([chr2, str(int(center2)-args.k), str(int(center2) + args.k), name2]) + '\n')
			elif line[0][0] == '#':
				firstLine = line
	process = subprocess.Popen('bedtools getfasta -fi ' + args.g + ' -bed ' + outfilename + 'Locs.bed' + ' -fo ' + outfilename + 'Genome.fa' + ' -name; ' +
							   'minimap2 -a ' + outfilename + 'Genome.fa ' + outfilename + "Filtered.fa" + ' > ' + outfilename + 'Remapped.sam; ' +
							   "sam2bed < " + outfilename + 'Remapped.sam' + ' > ' + outfilename + 'Remapped-unfilt.bed',stdout=subprocess.PIPE, shell=True)
	print(process.communicate()[0].strip())
	maxMapQ = 0
	with open(outfilename + 'Remapped-unfilt.bed', 'r') as remapped:
		for line in remapped:
			line = line.rstrip().split('\t')
			if int(line[4]) > maxMapQ: maxMapQ = int(line[4])
			fusions[line[0].split('->')[0]][line[0].split('->')[-1]]['mapQ'].append(int(line[4]))
			fusions[line[0].split('->')[0]][line[0].split('->')[-1]]['reads'].append(line[3])
			fusions[line[0].split('->')[0]][line[0].split('->')[-1]]['left'].append(int(line[1])-args.s)
			fusions[line[0].split('->')[0]][line[0].split('->')[-1]]['right'].append(int(line[2])-args.s)
	newFusions = open(outfilename + 'FusionsRemapped.tsv', 'w')
	firstLine.insert(2, 'confirmed reads')
	newFusions.write('\t'.join(firstLine) + '\n')
	doubleMappedReads = []
	for fusion in fusions:
		good = 0
		fusionReads = []
		mapScores = []
		for loc in fusions[fusion]:
			if loc not in ['line', 'conf reads']:
				if len(fusions[fusion][loc]['left']) > 0:
					leftAvg, rightAvg = sum(fusions[fusion][loc]['left'])/len(fusions[fusion][loc]['left']), \
										sum(fusions[fusion][loc]['right'])/len(fusions[fusion][loc]['right'])
					if abs(leftAvg + rightAvg) > 50:
						good += 1
						# if abs(leftAvg) > abs(rightAvg):
						# 	fusions[fusion][loc]['bp'] += max(fusions[fusion][loc]['right'])
						# else:
						# 	fusions[fusion][loc]['bp'] += min(fusions[fusion][loc]['left'])
						fusionReads.append(fusions[fusion][loc]['reads'])
						mapScores += fusions[fusion][loc]['mapQ']
						# if fusions[fusion][loc]['side'] == "3'":
						# 	fusions[fusion]['line'][5] = '-'.join(fusions[fusion]['line'][5].split('-')[:-1] + [str(fusions[fusion][loc]['bp'])])
						# else:
						# 	fusions[fusion]['line'][6] = '-'.join(fusions[fusion]['line'][6].split('-')[:-1] + [str(fusions[fusion][loc]['bp'])])
		if good >= 2:
			shared = list(set(fusionReads[0]) & set(fusionReads[1]))
			if len(shared) > 0:#good >= 2:
				for i in shared: doubleMappedReads.append(fusion + i)
				fusions[fusion]['line'].insert(2, str(len(shared)))
				fusions[fusion]['line'][3] = str(round((sum(mapScores)/len(mapScores))/float(maxMapQ), 3))
				newFusions.write('\t'.join(fusions[fusion]['line']) + '\n')
	newFusions.close()
	doubleMappedReads = set(doubleMappedReads)
	goodReadNames = []
	with open(outfilename + 'Remapped-unfilt.bed', 'r') as remapped, open(outfilename + 'Remapped.bed', 'w') as remapFilt:
		for line in remapped:
			line = line.split('\t')
			if line[0].split('->')[0] + line[3] in doubleMappedReads:
				remapFilt.write('\t'.join(line))
				goodReadNames.append(line[3])
	readsOut = open(outfilename + 'RemappedReads.bed', 'w')
	goodReadNames = set(goodReadNames)
	for line in open(outfilename + "Reads.bed", 'r'):
		temp = line.split('\t')
		if temp[3].split('-.-')[1] in goodReadNames:
			readsOut.write(line)


	process = subprocess.Popen('python3 ' + os.path.dirname(os.path.realpath(__file__)) + '/makeAlnSeq.py -f ' + outfilename +
							   'Genome.fa -r ' + outfilename + 'Remapped-unfilt.bed; rm ' + outfilename + 'Remapped-unfilt.bed',stdout=subprocess.PIPE, shell=True)
	print(process.communicate()[0].strip())


if not args.i:
	left, right = [], []
	for line in open(outfilename + 'Fusions.tsv', 'r'):
		if line[0] != '#':
			line = line.rstrip().split('\t')
			fusion = sorted(line[0].split('--'))
			# print(fusion)
			left.append(fusion[0])
			right.append(fusion[1])
	left = set(left)
	right = set(right)
	# print("left")
	# print(left)
	leftOut = open(outfilename + 'Reads-l.bed', 'w')
	rightOut = open(outfilename + 'Reads-r.bed', 'w')
	leftReads, rightReads = [], []
	c = 0
	for line in open(outfilename + 'Reads.bed', 'r'):
		line2 = line.strip().split('\t')
		geneName = line2[3].split('-.-')[2].split('/')[0]
		if geneName in left:
			c += 1
			leftOut.write(line)
		elif geneName in right:
			rightOut.write(line)
	leftOut.close()
	rightOut.close()
	# print(c)
	#print('python3 ' + args.f + ' collapse -g ' + args.g + ' -r ' + args.r + ' --generate_map -q ' + outfilename + 'Reads.bed -o ' + prefix + '.fusions',)
	#print('python3 ' + args.f + ' collapse -g ' + args.g + ' -r ' + args.r + ' --generate_map -q ' + outfilename + 'Reads-l.bed -o ' + prefix + '.fusions.l')
	process = subprocess.Popen(
		#collapse breaks.simplen/he_v2.3.5_pass.fastq --generate_map -q 17-03-2021he_v2.3.5_passReads-1.bed -o he.fusions.collapse
		'python3 ' + args.f + ' collapse --stringent --temp_dir temp_dir_l -g ' + args.g + ' -r ' + args.r + ' --generate_map -q ' + outfilename + 'Reads-l.bed -o ' + prefix + '.fusions.l' +
		'; python3 ' + args.f + ' collapse --stringent --temp_dir temp_dir_r -g ' + args.g + ' -r ' + args.r + ' --generate_map -q ' + outfilename + 'Reads-r.bed -o ' + prefix + '.fusions.r',
		stdout=subprocess.PIPE, shell=True)
	print(process.communicate()[0].strip())

if not args.j and os.path.exists(prefix + '.fusions.l.isoform.read.map.txt'):
	fusionisos = {}
	fusionHeader = ''
	for line in open(outfilename + 'Fusions.tsv', 'r'):
		if line[0] == '#': fusionHeader = line
		else:
			line = line.strip().split('\t')
			temp = line[0].split('--')
			fusionisos[line[0]] = {'reads':[], 'isos':[], 'line':line}
	for line in open(outfilename + 'Reads.bed', 'r'):
		line = line.split('\t')
		info = line[3].split('-.-')
		if info[0] in fusionisos.keys():
			fusionisos[info[0]]['reads'].append(info[1])
	lIsoSup, rIsoSup = {}, {}
	lIsoKey, rIsoKey = {}, {}
	c = 0
	for line in open(prefix + '.fusions.l.isoform.read.map.txt', 'r'):
		temp = line.strip().split('\t')
		lIsoKey['lIso' + str(c)] = temp[0]
		c += 1
		for i in temp[1].split(','):
			lIsoSup[i] = temp[0]#'lIso' + str(c) #temp[0]
	c = 0
	for line in open(prefix + '.fusions.r.isoform.read.map.txt', 'r'):
		temp = line.strip().split('\t')
		rIsoKey['rIso' + str(c)] = temp[0]
		c += 1
		for i in temp[1].split(','):
			rIsoSup[i] = temp[0]#'rIso' + str(c) #temp[0]
	lSet, rSet = set(lIsoSup.keys()), set(rIsoSup.keys())
	for i in fusionisos.keys():
		fusionisos[i]['reads'] = set(fusionisos[i]['reads'])
		for j in fusionisos[i]['reads']:
			inl, inr = '.', '.'
			# TESTING
			if j in lSet:
				if lIsoSup[j].split('-.-')[0]==i:
					inl = lIsoSup[j]
			if j in rSet:
				if rIsoSup[j].split('-.-')[0]==i:
					inr = rIsoSup[j]
			if inl != '.' or inr != '.':
				fusionisos[i]['isos'].append('-=-'.join([inl, inr]))
			# END TESTING
	c = 0
	#print(lSet)
	isoToCombName = {}
	fusionsOut = open(outfilename + 'IsoformFusions.tsv', 'w')
	fusionsOut.write(fusionHeader)
	#print(fusionisos)
	for i in fusionisos.keys():
		combIsoCounts = Counter(fusionisos[i]['isos'])
		#if c < 30: print(i, combIsoCounts)
		totIsos, doubleIsos, readsSupIsos = 0, 0, 0
		for j in combIsoCounts.keys():
			temp = j.split('-=-')
			numsides = 'single'
			if temp[0] != '.' and temp[1] != '.':
				doubleIsos += 1
				numsides = 'double'
			totIsos += 1
			#print(tempr)
			readsSupIsos += combIsoCounts[j]
			if temp[0] != '.':
				if temp[0].split('-.-')[1] not in isoToCombName: isoToCombName[temp[0].split('-.-')[1]] = []
				isoToCombName[temp[0].split('-.-')[1]].append("#" + i)
				isoToCombName[temp[0].split('-.-')[1]].append(str(combIsoCounts[j]) + '|combIso' + str(c) + '|' + numsides)
			if temp[1] != '.':
				if temp[1].split('-.-')[1] not in isoToCombName: isoToCombName[temp[1].split('-.-')[1]] = []
				isoToCombName[temp[1].split('-.-')[1]].append("#" + i)
				isoToCombName[temp[1].split('-.-')[1]].append(str(combIsoCounts[j]) + '|combIso' + str(c) + '|' + numsides)
			c += 1
		fusionisos[i]['line'][1] = str(doubleIsos) + '/' + str(totIsos) + '/' + str(readsSupIsos) + '/' + fusionisos[i]['line'][1]
		if totIsos > 0:
			fusionsOut.write('\t'.join(fusionisos[i]['line']) + '\n')
	readsOut = open(outfilename + 'IsoformReads.bed', 'w')
	#TESTING
	# multiGeneIsos = []
	# for i in isoToCombName.keys():
	# 	fusionList = []
	# 	for j in isoToCombName[i]:
	# 		if j[0] == '#': fusionList.append(j)
	# 	if len(Counter(fusionList).keys()) > 1:
	# 		multiGeneIsos.append([i, fusionList])
	# print(multiGeneIsos)
	# print(len(multiGeneIsos))
	c = 0
	written = []
	for i in ['l', 'r']:
		for line in open(prefix + '.fusions.' + i + '.isoforms.bed', 'r'):
			line = line.strip().split('\t')
			info = line[3].split('-.-')
			if info[1] in isoToCombName.keys():
				# c += 1
				# if c < 10:
				# 	print(isoToCombName[info[1]])
				for j in isoToCombName[info[1]]:
					if j[0] != '#':
						temp = info
						info[1] = j
						line[3] = '-.-'.join(info)
						if line[3] not in written:
							written.append(line[3])
							readsOut.write('\t'.join(line) + '\n')
	fusionsOut.close()
	readsOut.close()
	process = subprocess.Popen('rm -f ' + prefix + '.fusions.l.isoforms.fa ' + prefix + '.fusions.l.isoforms.bed ' + prefix + '.fusions.l.isoform.read.map.txt' + prefix + '.fusions.r.isoforms.fa ' + prefix + '.fusions.r.isoforms.bed ' + prefix + '.fusions.r.isoform.read.map.txt ' + outfilename + 'Reads-l.bed ' + outfilename + 'Reads-r.bed',stdout=subprocess.PIPE, shell=True)
	print(process.communicate()[0].strip())


# read on one side can be matched to multiple reads on the other (in combIsoCounts)
# must pick best
# why are reads from diff. fusions getting intp fusion?
# make isoform support stats lign up
# when multiple fusions in the same gene, it messes up
# check for any fusions with 2 unique loci - see if they look the same on the og version of testing section and new version
