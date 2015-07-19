import urllib,os,re,os.path,json,math,shutil
from zipfile import ZipFile
from bs4 import BeautifulSoup

from flask import (Flask, render_template, redirect,
                   url_for, request, make_response,
                   flash)

app = Flask(__name__)

DATA_DIR = os.path.abspath(os.path.dirname(__file__))

def cleanhtml(raw_html):
    cleanr =re.compile('<.*?>')
    cleantext = re.sub(cleanr,'', raw_html)
    return cleantext

def removeNonAscii(s): return "".join(i for i in s if ord(i)<128)

def txt(self):
    return self['filename'].split('/')[-1]

def localfile(self):
    filename = '%s/%s/%s/%s' % (DATA_DIR, self['cik'],txt(self)[:-4],txt(self))
    if os.path.exists(filename):
        return filename
    return None

def localpath(self):
    return '%s/%s/%s/' % (DATA_DIR, self['cik'],txt(self)[:-4])

def localcik(self):
    return '%s/%s/' % (DATA_DIR, self['cik'])

def html_link(self):
        return 'http://www.sec.gov/Archives/%s' % self['filename']

def html(self):
    filename = localfile(self)
    if not filename: 
        return None
    f = open(filename,'r').read()
    f_lower = f.lower()
    try:
        return f[f_lower.find('<html>'):f_lower.find('</html>')+4]
    except:
        print 'html tag not found'
        return f

def download(self):
    try: 
        os.mkdir(localcik(self))
    except:
        pass
    try:
        os.mkdir(localpath(self))
    except:
        pass
    os.chdir(localpath(self))
    if not os.path.exists(html_link(self).split('/')[-1]):
        os.system('wget %s' % html_link(self))     
    return localpath(self) + html_link(self).split('/')[-1]

def get_filing_list(year,qtr,data):
    url='ftp://ftp.sec.gov/edgar/full-index/%d/QTR%d/company.zip' % (year,qtr)
    quarter = "%s%s" % (year,qtr)

    print url
    # Download the data and save to a file
    fn='%s/company_%d_%d.zip' % (DATA_DIR, year,qtr)

    if not os.path.exists(fn):
        compressed_data=urllib.urlopen(url).read()
        print "downloading"
        fileout=file(fn,'w')
        fileout.write(compressed_data)
        fileout.close()

    # Extract the compressed file
    zip=ZipFile(fn)
    zdata=zip.read('company.idx')
    zdata = removeNonAscii(zdata)
    result=[]
    for r in zdata.split('\n')[10:]:
        date = r[86:98].strip()
        if date=='': date = None
        if r.strip()=='': continue
        form = r[62:74].strip()
        if form in data['filetype']: 
            filing={'name':r[0:62].strip(),
            'form':r[62:74].strip(),
            'cik':r[74:86].strip(),
            'date':date,
            'quarter': quarter,
            'filename':r[98:].strip()}
            result.append(filing)
    return result
    # Parse the fixed-length fields
def download_html(data):
    list_quarters = quarters_range(data)
    file_list = []
    for year, quarter in list_quarters:
        filing_list = get_filing_list(year, quarter, data)
        for item in filing_list:
            if data['fundname'].lower() in item['name'].lower():
                file_list.append(download(item))
    return file_list

def quarters_range(data):
    result = []
    start_date = data['start_date']
    end_date = data['end_date']
    m1 = int(start_date.split('/')[0])
    m2 = int(end_date.split('/')[0])
    y1 = int(start_date.split('/')[2])
    y2 = int(end_date.split('/')[2])
    quarter_to = int(math.ceil(m2/3.0))
    quarter_from = int(math.ceil(m1/3.0))
    for year in range(y1, y2+1):
        for quarter in range(1, 5):
            if y1 == year and quarter < quarter_from:
                continue
            if y2 == year and quarter > quarter_to:
                break
            result.append([year, quarter])
    return result

def valid_file(sents):
    list1 = ['BOARD APPROVAL OF INVESTMENT ADVISORY AGREEMENTS',
            'Board Approval of the Advisory Agreements',
            'Board Approval of the Renewal of the Investment Advisory Agreement',
            'Approval of Investment Advisory Agreement and Sub-Advisory Agreements',
            'APPROVAL OF INVESTMENT ADVISORY AGREEMENT',
            'Board Review of Management Agreements',
            'Board Approval of the Advisory Agreement',
            'INVESTMENT ADVISORY AGREEMENT DISCLOSURE',
            'APPROVAL OF INVESTMENT MANAGEMENT AGREEMENT',
            'BOARD APPROVAL OF INVESTMENT ADVISORY AGREEMENTS',
            'Trustees Approve Advisory Arrangements']
    rec = re.compile(r'|'.join(list1), flags=re.I)
    index = -1
    for i,sent in enumerate(sents):
        if re.search(rec, sent):
            return i
    return index        
def perform_search(data):
    file_list = download_html(data)
    print file_list
    #wrds = ["(L|l)ipper", "(M|m)orning(S|s)tar", "(I|i)nvestment (P|p)erformance", "(B|b)enchmark"]
    rec = re.compile(r'binvestment performance | lipper | morningstar| benchmark', flags=re.I)
    completeName = os.path.join(DATA_DIR, "result.txt")         
    to_file = open(completeName, 'w')
    to_file.write("<ul>")    
    for filepath in file_list:
        in_file = open(filepath,"r")
        text = str(in_file.read())
        soup = BeautifulSoup(text)
        text = soup.getText()
        text = removeNonAscii(text)
        #text = in_file.read()
        sents = re.split(r' *[\.\?!][\'"\)\]]* *', text)
        i=0
        for sent in sents:
            sents[i] = ' '.join(sent.split())
            sents[i] = cleanhtml(sents[i])
            i+=1
        i=valid_file(sents)
        if i==-1:
            continue
        length=len(sents)
        while (i <= (length-1)):
            if re.search(rec, sents[i]):
                if(i==0):   
                    to_file.write("<li>" + "<span style='color:grey'>" + sents[0] + ".\n </span>" + sents[1] + ".\n</li>")
                elif(i == (length-1)):
                    to_file.write("<li>" + sents[i-1] + ".\n " + "<span style='color:grey'>" + sents[i] + ".\n</span></li>")
                else:
                    to_file.write("<li>" + sents[i-1] + ".\n " + "<span style='color:grey'>" + sents[i] + ".\n</span> " + sents[i+1] + ".\n</li>")
            i+=1
        in_file.close()
    to_file.write("</ul>")    
    to_file.close()

def get_saved_data():
    try:
        data = json.loads(request.cookies.get('character'))
    except TypeError:
        data = {}
    return data

@app.route('/')
def home():
	return render_template("home.html", saves=get_saved_data())

@app.route('/result')
def result():
    read_file = open('/home/naivedya/test_files/result.txt','r')
    text = str(read_file.read())
    text = text.decode('utf-8')
    COLOR = 'red'
    regex   = re.compile(r'binvestment performance | lipper | morningstar| benchmark', flags=re.I)
    i = 0; 
    output = ""
    for m in regex.finditer(text):
        output += "".join([text[i:m.start()],
                            "<mark>",#"<strong><span style='color:%s'>" % COLOR,
                            text[m.start():m.end()],
                            "</mark>"])#"</span></strong>"])
        i = m.end()
    text = "".join([output, text[m.end():]]) #,"&lt;/html&gt;"])
    return render_template('result.html',saves=get_saved_data(),my_text=text)

@app.route('/save', methods=['POST'])
def save():
    response = make_response(redirect(url_for('result')))
    data = get_saved_data()
    data.update(dict(request.form.items()))
    data['fundname'] = data['fundname'].lower()
    data['filetype'] = request.form.getlist("filetype")
    file_path = '/home/naivedya/test_files/pre_computed/' + data['fundname'] + '.txt'
    if os.path.exists(file_path):
    	shutil.copyfile(file_path,"result.txt")
    else :
        perform_search(data)
    response.set_cookie('character', json.dumps(data))
    return response

app.run(debug=True, port=8200, host='localhost')