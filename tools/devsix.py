"""Fast dev loop: re-inject six/*.js + six/six.css into the already packaged dokko/web/index.html and refresh .br/.gz"""
import re,brotli,gzip
SIX=['core','net','safety','family','records','meds','care']
p='/home/claude/work/dokko/web/index.html'
s=open(p,encoding='utf-8').read()
css=open('/home/claude/work/six/six.css').read()
code='\n'.join(open('/home/claude/work/six/%s.js'%n).read() for n in SIX if __import__('os').path.exists('/home/claude/work/six/%s.js'%n))
assert '</script' not in code
code=re.sub(r'DoKKo(?!-Key)','TheHealthTracker',code);css=css.replace('DoKKo','TheHealthTracker')
s=re.sub(r'<style id="six-css">.*?</style>',lambda m:'<style id="six-css">'+css+'</style>',s,count=1,flags=re.S)
s=re.sub(r'<script id="six-js">.*?</script>',lambda m:'<script id="six-js">'+code+'\n</script>',s,count=1,flags=re.S)
open(p,'w',encoding='utf-8').write(s)
d=s.encode()
open(p+'.br','wb').write(brotli.compress(d,quality=5)); open(p+'.gz','wb').write(gzip.compress(d,6))
print('devsix ok',len(d))
