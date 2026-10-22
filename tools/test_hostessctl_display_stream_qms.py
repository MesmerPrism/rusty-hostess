"""Actual closed child seam, modeled transports; no listeners or devices."""
import io,json,pathlib,struct,subprocess,tempfile,threading,unittest
from tools.hostessctl import display_stream_qms as q

def line(v):return json.dumps(v,separators=(",",":")).encode()+b"\n"
def wire(s,packets=None):
 m=json.dumps(dict(invocation_id=s["invocationId"],generation=s["generation"])).encode();out=struct.pack(">8s6I",b"RMANVID1",1,1,640,480,0,len(m))+m
 for pts,flags,payload in (packets if packets is not None else [(0,2,b"config"),(0,1,b"key"),(33333,0,b"delta")]):out+=struct.pack(">QIIQQ",pts,flags,len(payload),100,200)+payload
 return out
class NativeOut:
 def __init__(self,p):self.p=p;self.index=0
 def readline(self,bound):
  if self.index==0:self.index+=1;return line(self.p.hello)
  if self.index==1:
   if self.p.options.get("missing_ack"):return b""
   if not self.p.stopped.wait(5):raise RuntimeError("test control never arrived")
   self.index+=1;return line(self.p.ack)
  return b""
class NativeIn:
 def __init__(self,p):self.p=p
 def write(self,value):self.p.controls.append(q.decode(value));self.p.stopped.set()
 def flush(self):pass
 def close(self):self.p.stopped.set()
class FailedStream:
 def readline(self,bound):raise OSError("modeled incomplete pipe")
class Native:
 def __init__(self,s,options):
  self.options=options;self.stopped=threading.Event();self.controls=[];self.exit_code=options.get("exit_code",0)
  self.hello=dict(schema="rusty.quest.display_stream.hello.v1",invocation_id=s["invocationId"],generation=s["generation"],stop_nonce=s["stopNonce"],pid=1234,uid=2000,start_ticks=5678)
  self.ack=dict(self.hello,schema="rusty.quest.display_stream.terminal.v1",stop_observed=True,worker_retired=True,resources_retired=options.get("release",True),state="retired",failure_code="NONE",failures=[])
  if options.get("wrong_nonce"):self.ack["stop_nonce"]="0"*32
  self.stdin=NativeIn(self);self.stdout=NativeOut(self);self.stderr=FailedStream() if options.get("incomplete_stderr") else io.BytesIO()
 def wait(self):return self.exit_code
class Media:
 def __init__(self,data):self.data=data
 def makefile(self,*a,**kw):return io.BytesIO(self.data)
 def close(self):pass
class Listener:
 def __init__(self,data):self.data=data
 def getsockname(self):return ("127.0.0.1",20000)
 def accept(self):return Media(self.data),None
 def close(self):pass
class FakeAdapter:
 def __init__(self,b,o,s,options):self.binding=b;self.output=o;self.start=s;self.options=options;self.commands=[];self.process=None
 def guard(self):
  if self.options.get("guard_failure"):raise ValueError("modeled unavailable peer")
 def adb(self,args,check=True):
  self.commands.append(args)
  if args[:2]==["reverse","--no-rebind"]:self.reverse=args[2:]
  if args==["reverse","--list"]:
   row=[self.reverse[0],"tcp:9999"] if self.options.get("foreign_reverse") else self.reverse
   return subprocess.CompletedProcess(args,0,("model "+" ".join(row)+"\n").encode(),b"")
  data=(self.binding["shellJar"]["sha256"]+"  producer.jar\n").encode() if args[:2]==["shell","sha256sum"] else b"";return subprocess.CompletedProcess(args,0,data,b"")
 def listener(self):return Listener(wire(self.start))
 def launch(self,command):self.commands.append(command);self.process=Native(self.start,self.options);return self.process
 def require_actor(self,h):
  if self.options.get("actor_failure"):raise ValueError("actor changed")
  assert h["pid"]==1234 and h["start_ticks"]==5678
 def require_absent(self,h):
  if self.options.get("still_live"):raise ValueError("remote still live")
class OwnedDisplayTests(unittest.TestCase):
 def fixture(self,d,index="1"):
  d=pathlib.Path(d);adb=d/"model-adb";jar=d/"model-jar"
  if not adb.exists():adb.write_bytes(b"modeled executable");jar.write_bytes(b"modeled source jar")
  b=dict(schema="rusty.hostess.display_stream.owner_binding.v1",adb=q.pin(adb),shellJar=q.pin(jar),transport="model-target",canonical="model-device",bootId="11111111-1111-1111-1111-111111111111",remotePort=19079,displayId=0,width=640,height=480,fps=30,bitrateBps=8000000)
  path=d/("binding"+index+".json");path.write_bytes(line(b));return dict(schema="questms.display.start.v1",sourceId="model-Q",invocationId=index*32,generation="model-generation",stopNonce="f"*32,ownerBindingRef=q.pin(path),outputDirectory=str(d/("out"+index)))
 def execute(self,s,**options):
  adapters=[]
  def factory(b,o):a=FakeAdapter(b,o,s,options);adapters.append(a);return a
  stop={k:s[k] for k in q.STOP if k!="schema"};stop["schema"]="questms.display.stop.v1";out=io.BytesIO();result=q.run(s,io.BytesIO(line(stop)),out,adapter_factory=factory);return result,json.loads((pathlib.Path(s["outputDirectory"])/"TERMINAL.json").read_bytes()),adapters[0],out.getvalue()
 def test_closed_start_stop_and_pinned_binding(self):
  with tempfile.TemporaryDirectory() as d:
   s=self.fixture(d);self.assertEqual(q.checked_start(line(s)),s);self.assertEqual(q.read_binding(s["ownerBindingRef"])["width"],640)
   with self.assertRaises(ValueError):q.checked_start(line(dict(s,extra=True)))
   with self.assertRaises(ValueError):q.checked_start(line(s).replace(b'"sourceId":',b'"sourceId":"duplicate","sourceId":'))
   stop={k:s[k] for k in q.STOP if k!="schema"};stop["schema"]="questms.display.stop.v1"
   with self.assertRaises(ValueError):q.checked_stop(line(dict(stop,stopNonce="0"*32)),s)
   with self.assertRaises(ValueError):q.read_line(io.BytesIO(b"x"*4097+b"\n"))
 def test_actual_once_adapter_repeated_start_stop_unique_namespaces(self):
  with tempfile.TemporaryDirectory() as d:
   s=self.fixture(d);result,t,a,raw=self.execute(s);self.assertEqual(result,0);self.assertEqual(t["state"],"retired");self.assertTrue(t["resourcesRetired"]);self.assertEqual(raw,wire(s));self.assertEqual(len(a.process.controls),1)
   commands=repr(a.commands);self.assertNotIn("pkill",commands);self.assertNotIn("proximity",commands);self.assertNotIn("settings",commands);self.assertIn("rusty-quest-display-"+s["invocationId"],commands)
   with self.assertRaises(FileExistsError):self.execute(s)
   s2=self.fixture(d,"2");self.assertEqual(self.execute(s2)[0],0);self.assertNotEqual(s["invocationId"],s2["invocationId"])
 def test_native_nonzero_never_promoted_by_ack(self):
  with tempfile.TemporaryDirectory() as d:
   result,t,a,_=self.execute(self.fixture(d),exit_code=1);self.assertNotEqual(result,0);self.assertEqual(t["nativeChildExitCode"],1);self.assertEqual(t["state"],"unknown");self.assertFalse(any(c[:2]==["shell","rm"] for c in a.commands))
 def test_wrong_nonce_release_or_live_actor_retains_scope(self):
  for options in [dict(wrong_nonce=True),dict(release=False),dict(still_live=True),dict(actor_failure=True),dict(foreign_reverse=True),dict(missing_ack=True),dict(incomplete_stderr=True)]:
   with self.subTest(options=options),tempfile.TemporaryDirectory() as d:
    result,t,a,_=self.execute(self.fixture(d),**options);self.assertNotEqual(result,0);self.assertEqual(t["state"],"unknown");self.assertFalse(any("pkill" in c for c in a.commands));self.assertFalse(any(c[:2]==["shell","rm"] for c in a.commands))
 def test_unavailable_peer_has_no_start_effect(self):
  with tempfile.TemporaryDirectory() as d:
   result,t,a,_=self.execute(self.fixture(d),guard_failure=True);self.assertNotEqual(result,0);self.assertEqual(t["state"],"failed");self.assertEqual(a.commands,[])
 def test_actual_wire_config_key_pts_truncation(self):
  with tempfile.TemporaryDirectory() as d:
   s=self.fixture(d);stats=dict(packets=0);out=io.BytesIO();raw=wire(s);q.pump_media(io.BytesIO(raw),out,s,stats);self.assertEqual(out.getvalue(),raw);self.assertEqual(stats["packets"],3)
   for packets in [[(0,1,b"key")],[(0,2,b"config"),(1,0,b"delta")],[(0,2,b"config"),(10,1,b"key"),(10,0,b"duplicate")],[(0,8,b"bad")]]:
    with self.assertRaises(ValueError):q.pump_media(io.BytesIO(wire(s,packets)),io.BytesIO(),s,dict(packets=0))
   with self.assertRaises(ValueError):q.pump_media(io.BytesIO(raw[:-1]),io.BytesIO(),s,dict(packets=0))
if __name__=="__main__":unittest.main()
