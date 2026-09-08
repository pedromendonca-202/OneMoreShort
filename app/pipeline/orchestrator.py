"""Small persistent workflow for the manual visual-generation handoff."""
from __future__ import annotations
import random
from datetime import datetime,UTC
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.core.db import get_engine,init_db,session_scope
from app.core.ids import new_production_id
from app.core.models import Production,Topic,Research as ResearchRow,Script as ScriptRow,Storyboard as StoryRow,ContinuityBible as BibleRow
from app.core.states import State
from app.core.storage import Storage
from app.llm.router import build_llm
from app.llm.mock import MockLLM
from app.manual_video.workflow import export_prompts,collect_manual_segments,inbox_for
from app.research.schemas import TopicScore,KnowledgeContext,StrategyWeights
from app.research.deep_research import deep_research
from app.scripting.generator import generate_script
from app.storyboard.generator import generate_storyboard
from app.continuity.bible import build_bible
from app.core.errors import HumanActionRequired

class Orchestrator:
 def __init__(self,settings:Settings):
  self.settings=settings; self.engine=get_engine(settings.paths.database_url);init_db(self.engine);self.storage=Storage(settings.resolve(settings.paths.storage_root))
 def new_production(self)->str:
  with session_scope(self.engine) as s:
   pid=new_production_id(s,datetime.now(UTC).date());s.add(Production(id=pid,state=State.DISCOVERING,config_snapshot=self.settings.snapshot()));return pid
 def prepare(self,pid:str):
  with session_scope(self.engine) as s:
   p=s.get(Production,pid)
   if not p:raise ValueError(f"unknown production {pid}")
   llm=build_llm(self.settings)
   if not p.topics:
    topic=self._discover_topic(llm)
    s.add(Topic(production_id=pid,topic=topic.topic,category=topic.category,selected=True,final_score=topic.final_score,reasons=topic.reasons));p.state=State.SELECTED;s.flush()
   selected=next((topic for topic in s.query(Topic).filter_by(production_id=pid) if topic.selected),None)
   if selected is None:raise RuntimeError("selected topic was not persisted")
   score=TopicScore(topic=selected.topic,category=selected.category,trend_score=70,viral_potential=70,us_relevance=80,competition=30,shorts_fit=90,originality=80,risk=10,final_score=selected.final_score,reasons=selected.reasons or [])
   research=deep_research(llm,score.topic,use_search=self.settings.is_live)
   script=generate_script(llm,score,research,KnowledgeContext(),self.settings)
   storyboard=generate_storyboard(llm,script,self.settings); bible=build_bible(llm,script,storyboard)
   if not p.research:s.add(ResearchRow(production_id=pid,topic=score.topic,data=research.model_dump(),sources=[]))
   if not p.script:s.add(ScriptRow(production_id=pid,data=script.model_dump(),text=script.text,hook_type=script.hook_type.value,ending_type=script.ending_type,total_words=script.total_words,est_duration_s=script.est_duration_s))
   if not p.storyboard:s.add(StoryRow(production_id=pid,data=storyboard.model_dump(),visual_style=storyboard.visual_style))
   if not p.bible:s.add(BibleRow(production_id=pid,data=bible.model_dump()))
   package=export_prompts(pid,storyboard,bible,self.storage,self.settings);p.state=State.GENERATING;s.flush()
   return package
 def _discover_topic(self,llm):
  if self.settings.mode!="live":
   return TopicScore(topic="A surprising science fact",category="science",trend_score=70,viral_potential=70,us_relevance=80,competition=30,shorts_fit=90,originality=80,risk=10,final_score=78,reasons=["deterministic mock discovery"])
  from app.trends.reddit_source import RedditSource
  from app.trends.news_rss_source import GoogleNewsRSSSource
  from app.trends.hackernews_source import HackerNewsSource
  from app.trends.wikipedia_source import WikipediaTopViewedSource
  from app.trends.gtrends_rss_source import GoogleTrendsRSSSource
  from app.trends.youtube_source import YouTubeTrendSource
  from app.trends.aggregator import aggregate
  from app.research.scorer import score_topics
  from app.research.selector import select_topic
  sources=[RedditSource(self.settings.trends.reddit_subreddits,timeout_s=self.settings.trends.http_timeout_s),GoogleNewsRSSSource(region=self.settings.trends.region,language=self.settings.trends.language,timeout_s=self.settings.trends.http_timeout_s),HackerNewsSource(timeout_s=self.settings.trends.http_timeout_s),WikipediaTopViewedSource(timeout_s=self.settings.trends.http_timeout_s),GoogleTrendsRSSSource(region=self.settings.trends.region,timeout_s=self.settings.trends.http_timeout_s)]
  if self.settings.google_api_key:sources.append(YouTubeTrendSource(self.settings.google_api_key.get_secret_value(),region=self.settings.trends.region,categories=self.settings.trends.youtube_categories,timeout_s=self.settings.trends.http_timeout_s))
  signals=[signal for source in sources for signal in source.fetch(self.settings.trends.per_source_limit)]
  clusters=aggregate(signals,llm=llm,max_candidates=self.settings.trends.max_candidates)
  if not clusters:raise RuntimeError("no usable trend signals; retry later or check network/source configuration")
  scores=score_topics(llm,clusters,knowledge=KnowledgeContext())
  return select_topic(scores, StrategyWeights(), rng=random.Random())[0]
 def collect(self,pid:str):
  with session_scope(self.engine) as s:
   p=s.get(Production,pid)
   if not p:raise ValueError(f"unknown production {pid}")
   result=collect_manual_segments(pid,self.storage,s,self.settings);p.state=State.EDITING;return result
 def finish(self,pid:str):
  from app.scripting.schemas import Script
  from app.audio.narration import narrate
  from app.audio.tts.mock import MockTTS
  from app.audio.tts.edge import EdgeTTS
  from app.audio.mixer import mix_audio
  from app.captions.aligner import align_words,build_phrases
  from app.captions.ass_renderer import render_ass
  from app.captions.style import CaptionStyle
  from app.editing.render import render_final
  from app.metadata.schemas import VideoMetadata
  from app.quality.gate import run_quality_gate
  from app.youtube.mock import MockYouTubeClient
  from app.youtube.uploader import GoogleYouTubeClient
  from app.youtube.auth import get_credentials
  from app.core.models import Upload,FinalVideo,VideoMetadata as MetadataRow
  with session_scope(self.engine) as s:
   p=s.get(Production,pid)
   if not p or not p.script:raise ValueError("production must be prepared and collected first")
   concat=self.storage.path_for(pid,"renders","segments_concat.mp4")
   if not concat.exists():raise ValueError("collect clips before finish")
   script=Script.model_validate(p.script.data); llm=build_llm(self.settings)
   tts=MockTTS() if self.settings.mode=="mock" else EdgeTTS(self.settings.tts.edge_voice)
   narration=narrate(script,tts,llm,self.storage,pid,self.settings.video.max_duration_s)
   mixed=mix_audio(concat,narration,None,self.storage.path_for(pid,"audio","mixed.wav"),self.settings)
   ass=render_ass(build_phrases(align_words(narration),self.settings.captions.max_words),CaptionStyle(font=self.settings.captions.font,font_size=self.settings.captions.font_size),self.storage.path_for(pid,"captions","captions.ass"))
   final=render_final(concat,mixed,ass,None,self.storage.path_for(pid,"renders","OneMoreShort_Final.mp4"),self.settings.video.max_duration_s,self.storage.root)
   meta=VideoMetadata(title=script.title_working,description="Original short generated by OneMoreShort.",hashtags=["#Shorts","#Science","#OneMoreShort"],tags=["shorts"],category_id=self.settings.upload.default_category_id)
   report=run_quality_gate(final,list(p.segments),narration,ass,meta,[x.continuity_score for x in p.segments],llm,self.settings)
   s.merge(FinalVideo(production_id=pid,path=str(final),probe=None,quality_report=report.model_dump(),passed=report.passed))
   s.merge(MetadataRow(production_id=pid,title=meta.title,description=meta.description,tags=meta.tags,hashtags=meta.hashtags,category_id=meta.category_id,thumbnail_time_s=meta.thumbnail_time_s))
   if not report.passed:p.state=State.NEEDS_REVIEW;return final
   p.state=State.READY
   if self.settings.upload.enabled:
    yt=MockYouTubeClient() if self.settings.mode=="mock" else GoogleYouTubeClient(get_credentials(self.settings.resolve(self.settings.youtube_client_secret_path),self.settings.resolve(self.settings.youtube_token_path),["https://www.googleapis.com/auth/youtube.upload"]))
    out=yt.upload(final,meta,self.settings.upload.visibility,meta.publish_at)
    s.merge(Upload(production_id=pid,youtube_video_id=out.video_id,url=out.url,privacy=self.settings.upload.visibility,status=out.status,uploaded_at=datetime.now(UTC)));p.state=State.PUBLISHED
   return final
 def status(self,pid:str):
  with session_scope(self.engine) as s:
   p=s.get(Production,pid)
   if not p:raise ValueError(f"unknown production {pid}")
   return {"id":p.id,"state":p.state.value,"cost_usd":p.cost_usd,"segments":len(p.segments)}
