"""Minimal binary FBX reader: returns the first Geometry mesh as vertices and triangles."""
import struct, zlib, numpy as np
def read_fbx(path):
    d=open(path,'rb').read(); ver=struct.unpack_from('<I',d,23)[0]
    big=ver>=7500
    def node(o):
        if big: end,nprop,plen,nl=struct.unpack_from('<QQQB',d,o); o+=25
        else: end,nprop,plen,nl=struct.unpack_from('<IIIB',d,o); o+=13
        if end==0: return None,o
        name=d[o:o+nl].decode(); o+=nl; props=[]; po=o
        for _ in range(nprop):
            t=chr(d[o]); o+=1
            if t in 'YCFDIL':
                f={'Y':'<h','C':'<?','F':'<f','D':'<d','I':'<i','L':'<q'}[t]
                props.append(struct.unpack_from(f,d,o)[0]); o+=struct.calcsize(f)
            elif t in 'fdilb':
                n,enc,cl=struct.unpack_from('<III',d,o); o+=12
                raw=d[o:o+cl]; o+=cl
                if enc: raw=zlib.decompress(raw)
                props.append(np.frombuffer(raw,{'f':'<f4','d':'<f8','i':'<i4','l':'<i8','b':'u1'}[t]))
            elif t in 'SR':
                n=struct.unpack_from('<I',d,o)[0]; o+=4; props.append(d[o:o+n]); o+=n
        o=po+plen; kids=[]
        while o<end:
            k,o=node(o)
            if k is None: break
            kids.append(k)
        return (name,props,kids),end
    o=27; root=[]
    while o<len(d):
        n,o=node(o)
        if n is None: break
        root.append(n)
    return root
def find(nodes,name):
    for n in nodes:
        if n[0]==name: yield n
        yield from find(n[2],name)
def mesh(path):
    r=read_fbx(path); g=next(find(r,'Geometry'))
    v=next(n for n in g[2] if n[0]=='Vertices')[1][0].reshape(-1,3)
    idx=next(n for n in g[2] if n[0]=='PolygonVertexIndex')[1][0]
    # decode polygons
    polys=[];cur=[]
    for i in idx:
        if i<0: cur.append(~i); polys.append(cur); cur=[]
        else: cur.append(i)
    tris=[]
    for p in polys:
        for k in range(1,len(p)-1): tris.append((p[0],p[k],p[k+1]))
    return v,np.array(tris)
