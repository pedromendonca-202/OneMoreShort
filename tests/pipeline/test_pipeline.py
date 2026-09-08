from app.pipeline.orchestrator import Orchestrator
from app.editing.synth import synth_segment
from app.manual_video.workflow import inbox_for
def test_new_production_persists(settings):
 o=Orchestrator(settings);pid=o.new_production();assert o.status(pid)["state"]=="DISCOVERING"
def test_manual_mock_pipeline_collects_and_renders(settings):
 settings.veo.duration_seconds=1;settings.video.max_duration_s=5
 o=Orchestrator(settings);pid=o.new_production();o.prepare(pid)
 inbox=inbox_for(pid,o.storage,settings)
 for i in range(1,6):synth_segment(inbox/f"segment_{i}.mp4",1,"black",str(i),with_audio=True)
 o.collect(pid);final=o.finish(pid)
 assert final.exists() and o.status(pid)["state"]=="READY"
